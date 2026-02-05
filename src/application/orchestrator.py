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

    # --- FIX: Headers avec API-KEY pour les services d'infrastructure ---
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

    yt_match = re.search(r"(https?://(?:www\.)?youtube\.com/watch\?v=[^\s&]+)", raw_prompt)
    if yt_match:
        youtube_url = yt_match.group(1)
        conv_type = "CHAT_WITH_YOUTUBE_VIDEO"
        logger.info(f"ORCHESTRATOR | Mode YouTube détecté: {youtube_url}")

    if request_data.get("content_type") == "IMAGE_GENERATOR":
        logger.info("ORCHESTRATOR | Mode Génération d'Image activé")
        prompt_object = {
            "prompt": raw_prompt,
            "language": request_data.get("language", "English"),
            "n": int(request_data.get("n", 1)),
            "size": request_data.get("size", "1024x1024"),
        }
        return {
            "type": "IMAGE_GENERATOR",
            "session_id": f"gen-{uuid.uuid4()}",
            "image_paths": [],
            "prompt_object": prompt_object,
        }

    prompt_object = {
        "prompt": raw_prompt,
        "isMixed": request_data.get("is_mixed", False),
        "webSearch": request_data.get("web_search", False),
        "numOfSite": int(request_data.get("num_of_site", 1)),
        "maxWord": int(request_data.get("max_word", 500)),
    }

    if image_paths:
        prompt_object["imageList"] = image_paths

    # --- FIX: La session_id échouait à cause du header API-KEY manquant dans create_1min_conversation ---
    session_id = create_1min_conversation(
        api_key=api_key,
        model=model_name,
        conv_type=conv_type,
        title=f"Chat_{model_name[:20]}",
        file_ids=file_ids,
        youtube_url=youtube_url,
        prompt_object=prompt_object,
    )

    if not session_id:
        logger.warning(
            "ORCHESTRATOR | Session non créée par 1min.ai. Utilisation d'un ID temporaire."
        )
        session_id = str(uuid.uuid4())

    return {
        "type": conv_type,
        "session_id": session_id,
        "image_paths": image_paths,
        "prompt_object": prompt_object,
    }
