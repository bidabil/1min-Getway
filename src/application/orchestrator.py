# src/application/orchestrator.py

import logging
import re
import uuid

from ..config import ONE_MIN_ASSET_API_URL
from ..infrastructure.asset_service import upload_image_to_1min
from ..infrastructure.one_min_client import create_1min_conversation

logger = logging.getLogger("1min-gateway.orchestrator")


def resolve_conversation_context(api_key, model_name, messages, request_data=None):
    request_data = request_data or {}
    conv_type = "CHAT_WITH_AI"
    image_paths = []
    file_ids = []
    youtube_url = None

    last_message = messages[-1] if messages else {}
    content = last_message.get("content", "")

    # --- Headers pour upload image ---
    asset_headers = {"API-KEY": api_key, "Authorization": f"Bearer {api_key}"}

    raw_prompt = ""
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                raw_prompt += part.get("text", "")
            elif part.get("type") == "image_url":
                try:
                    logger.info("ORCHESTRATOR | Détection d'image, tentative d'upload...")
                    path = upload_image_to_1min(part, asset_headers, ONE_MIN_ASSET_API_URL)
                    if path:
                        image_paths.append(path)
                        conv_type = "CHAT_WITH_IMAGE"
                except Exception as e:
                    logger.error(f"ORCHESTRATOR | Échec upload image: {str(e)}")
    else:
        raw_prompt = str(content)

    # --- NOUVELLE LOGIQUE : On ne crée PAS de conversation pour les cas simples ---

    # Cas 1: Image Generation (AMÉLIORÉ avec plus de paramètres)
    if request_data.get("content_type") == "IMAGE_GENERATOR":
        logger.info("ORCHESTRATOR | Mode Génération d'Image activé")

        # Construire prompt_object avec TOUS les paramètres
        prompt_object = {
            "prompt": raw_prompt,
            "language": request_data.get("language", "English"),
            "n": int(request_data.get("n", 1)),
            "size": request_data.get("size", "1024x1024"),
            # --- NOUVEAUX PARAMÈTRES POUR IMAGE ---
            "aspect_ratio": request_data.get("aspect_ratio", "1:1"),
            "output_format": request_data.get("output_format", "webp"),
            "num_outputs": int(request_data.get("n", 1)),  # Même que 'n'
            "style": request_data.get("style", ""),
            "negative_prompt": request_data.get("negative_prompt", ""),
            "mode": request_data.get("mode", "fast"),
            "isNiji6": bool(request_data.get("is_niji6", False)),
            "maintainModeration": bool(request_data.get("maintain_moderation", True)),
            "aspect_width": int(request_data.get("aspect_width", 1)),
            "aspect_height": int(request_data.get("aspect_height", 1)),
        }

        # Nettoyer les paramètres vides
        prompt_object = {k: v for k, v in prompt_object.items() if v not in [None, "", 0, False]}

        return {
            "type": "IMAGE_GENERATOR",
            "session_id": f"gen-{uuid.uuid4()}",
            "image_paths": [],
            "prompt_object": prompt_object,
        }

    # Cas 2: YouTube (nécessite une vraie conversation)
    yt_match = re.search(r"(https?://(?:www\.)?youtube\.com/watch\?v=[^\s&]+)", raw_prompt)
    if yt_match:
        youtube_url = yt_match.group(1)
        conv_type = "CHAT_WITH_YOUTUBE_VIDEO"
        logger.info(f"ORCHESTRATOR | Mode YouTube détecté: {youtube_url}")

        # Pour YouTube, on DOIT créer une conversation
        session_id = create_1min_conversation(
            api_key=api_key,
            model=model_name,
            conv_type=conv_type,
            title=f"Chat_{model_name[:20]}",
            file_ids=file_ids,
            youtube_url=youtube_url,
            prompt_object=None,
        )

        if not session_id:
            logger.warning("ORCHESTRATOR | Session YouTube non créée.")
            session_id = str(uuid.uuid4())

    # Cas 3: Chat simple (sans historique complexe) - ON NE CRÉE PAS DE CONVERSATION
    elif len(messages) <= 2:  # Un ou deux messages max
        # On utilise directement le type comme ID (ex: "CHAT_WITH_AI")
        session_id = conv_type
        logger.info(f"ORCHESTRATOR | Mode simple - Utilisation du type comme ID: {session_id}")

    # Cas 4: Chat avec historique long - On crée une vraie conversation
    else:
        logger.info("ORCHESTRATOR | Historique long détecté - Création conversation...")
        session_id = create_1min_conversation(
            api_key=api_key,
            model=model_name,
            conv_type=conv_type,
            title=f"Chat_{model_name[:20]}",
            file_ids=file_ids,
            youtube_url=youtube_url,
            prompt_object=None,
        )

        if not session_id:
            logger.warning("ORCHESTRATOR | Session non créée. Utilisation du type comme ID.")
            session_id = conv_type

    # Construction du prompt_object (commun à tous les cas SAUF Image Generation)
    prompt_object = {
        "prompt": raw_prompt,
        "isMixed": bool(request_data.get("is_mixed", False)),
        "webSearch": bool(request_data.get("web_search", False)),
        "numOfSite": int(request_data.get("num_of_site", 1)),
        "maxWord": int(request_data.get("max_word", 500)),
    }

    # --- AJOUTER metadata pour multi-AI chat ---
    metadata = {}
    if request_data.get("message_group"):
        metadata["messageGroup"] = str(request_data.get("message_group"))
    if request_data.get("user_id"):
        metadata["userId"] = str(request_data.get("user_id"))

    if metadata:
        prompt_object["metadata"] = metadata

    # --- Pour image analysis (CHAT_WITH_IMAGE) ---
    if image_paths:
        prompt_object["imageList"] = image_paths
        # Paramètres spécifiques aux images
        prompt_object["imageDetail"] = request_data.get("image_detail", "auto")
        prompt_object["maxTokens"] = int(request_data.get("max_tokens", 300))

    # Nettoyer les paramètres vides
    prompt_object = {k: v for k, v in prompt_object.items() if v not in [None, ""]}

    return {
        "type": conv_type,
        "session_id": session_id,
        "image_paths": image_paths,
        "prompt_object": prompt_object,
    }
