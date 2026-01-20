#

import re
from src import logger, upload_image_to_1min, ONE_MIN_ASSET_URL
from src.infrastructure.conversation_service import create_1min_conversation

def resolve_conversation_context(api_key, model_name, current_user_message, request_data=None):
    """
    Analyse globale : Détecte si la requête est une Feature (outil) ou une Conversation (Chat).
    Supporte Magic Art, GPT Image 1, DALL-E, Dzine, Leonardo AI et les outils de texte/multimédia.
    """
    request_data = request_data or {}
    conv_type = "CHAT_WITH_AI"
    session_id = None
    image_paths = []
    file_ids = []
    youtube_url = None
    prompt_object = None

    # --- 1. EXTRACTION DU CONTENU (TEXTE, IMAGES, DOCUMENTS) ---
    raw_prompt = ""
    if isinstance(current_user_message, list):
        for item in current_user_message:
            if 'text' in item: 
                raw_prompt = item['text']
            if 'image_url' in item:
                path = upload_image_to_1min(item, api_key, ONE_MIN_ASSET_URL)
                if path: 
                    image_paths.append(path)
                    conv_type = "CHAT_WITH_IMAGE"
            elif 'file_id' in item:
                file_ids.append(item['file_id'])
                conv_type = "CHAT_WITH_PDF"
    else:
        raw_prompt = current_user_message

    # --- 2. DÉTECTION DES TOOLS / FEATURES (CONTENT_TYPE) ---
    content_type = request_data.get('content_type')
    
    if content_type:
        # Initialisation du prompt_object de base pour les outils
        prompt_object = {
            "prompt": raw_prompt,
            "tone": request_data.get('tone', 'professional'),
            "language": request_data.get('language', 'French')
        }

        # A. LOGIQUE IMAGE_GENERATOR (Multi-modèles)
        if content_type == "IMAGE_GENERATOR":
            conv_type = "IMAGE_GENERATOR"
            
            # --- Cas Leonardo AI (Phoenix, Lightning, Anime) ---
            is_leonardo = any(key.startswith("leonardo_") for key in request_data.keys()) or \
                          model_name in ["6b645e3a-d64f-4341-a6d8-7a3690fbf042", 
                                       "b24e16ff-06e3-43eb-8d33-4416c2d75876", 
                                       "e71a1c2f-4f80-4800-934f-2c68979d8cc8"]
            if is_leonardo:
                prompt_object.update({
                    "size": request_data.get('size', "1024x1024"),
                    "n": request_data.get('n', 1),
                    "negativePrompt": request_data.get('negative_prompt', "")
                })
                # Collecte dynamique de tous les paramètres préfixés leonardo_
                for key, value in request_data.items():
                    if key.startswith("leonardo_"):
                        prompt_object[key] = value
                # Image Guidance
                if image_paths:
                    prompt_object["leonardo_image_prompts"] = image_paths[:4]

            # --- Cas GPT Image 1 & Mini ---
            elif "gpt-image-1" in model_name:
                prompt_object.update({
                    "n": request_data.get('n', 1),
                    "size": request_data.get('size', "1024x1024"),
                    "quality": request_data.get('quality', "medium"),
                    "style": request_data.get('style', "vivid"),
                    "output_format": request_data.get('output_format', "png"),
                    "output_compression": request_data.get('output_compression', 85),
                    "background": request_data.get('background', "opaque")
                })

            # --- Cas Dzine ---
            elif model_name == "dzine":
                prompt_object.update({
                    "style_code": request_data.get('style_code', "Style-7feccf2b-f2ad-43a6-89cb-354fb5d928d2"),
                    "style_base_model": request_data.get('style_base_model', "S"),
                    "quality": request_data.get('quality', "HIGH"),
                    "n": request_data.get('n', 1),
                    "output_format": request_data.get('output_format', "webp"),
                    "size": request_data.get('size', "1024x1024"),
                    "style_intensity": request_data.get('style_intensity', 0.8),
                    "face_match": request_data.get('face_match', False)
                })
                if prompt_object["face_match"] and image_paths:
                    prompt_object["face_match_image"] = image_paths[0]

            # --- Cas Magic Art & DALL-E (Par défaut) ---
            else:
                prompt_object.update({
                    "n": 1 if "dall-e-3" in model_name else request_data.get('n', 4),
                    "size": request_data.get('size', "1024x1024"),
                    "style": request_data.get('style', "vivid"),
                    "quality": request_data.get('quality', "standard")
                })
                # Paramètres spécifiques Magic Art (Midjourney style)
                if "magic-art" in model_name:
                    prompt_object.update({
                        "mode": request_data.get('mode', 'fast'),
                        "aspect_width": request_data.get('aspect_width', 1),
                        "aspect_height": request_data.get('aspect_height', 1),
                        "stylize": request_data.get('stylize', 100)
                    })
                    if image_paths:
                        ref_key = "omni_reference" if "magic-art_7_0" in model_name else "character_reference"
                        prompt_object[ref_key] = image_paths[0]

        # B. LOGIQUE TEXT TOOLS (Summarizer, Translator, etc.)
        elif content_type == "SUMMARIZER":
            conv_type = "SUMMARIZER"
            prompt_object.update({"numberOfBullet": request_data.get('bullets', 5), "numberOfWord": request_data.get('words_per_bullet', 20)})
        elif content_type == "CONTENT_TRANSLATOR":
            conv_type = "CONTENT_TRANSLATOR"
            prompt_object.update({"originalLanguage": request_data.get('from_lang', 'en'), "targetLanguage": request_data.get('to_lang', 'fr')})
        elif content_type == "BLOG_ARTICLE":
            conv_type = "CONTENT_GENERATOR_BLOG_ARTICLE"
            prompt_object.update({"numberOfWord": request_data.get('words', 1000)})
        elif content_type in ["GRAMMAR_CHECKER", "KEYWORD_RESEARCH", "EMAIL", "GOOGLE_ADS"]:
            conv_type = f"CONTENT_GENERATOR_{content_type}" if content_type != "GRAMMAR_CHECKER" else content_type

        # Sortie pour toutes les Features
        is_feature = conv_type in ["IMAGE_GENERATOR", "SUMMARIZER", "GRAMMAR_CHECKER", "CONTENT_TRANSLATOR"] or conv_type.startswith("CONTENT_GENERATOR")
        if is_feature:
            return {
                "type": conv_type,
                "session_id": conv_type,
                "image_paths": image_paths,
                "prompt_object": prompt_object
            }

    # --- 3. LOGIQUE CHAT & MULTIMÉDIA ---
    
    # Cas Vision (Chat avec Image)
    if conv_type == "CHAT_WITH_IMAGE":
        return {
            "type": "CHAT_WITH_IMAGE",
            "session_id": None,
            "image_paths": image_paths,
            "prompt_object": {"prompt": raw_prompt, "imageList": image_paths, "webSearch": request_data.get('web_search', False)}
        }

    # Cas YouTube (Détection URL)
    if isinstance(raw_prompt, str) and "youtube.com/watch" in raw_prompt:
        yt_match = re.search(r'(https?://www.youtube.com/watch\?v=[^\s&]+)', raw_prompt)
        if yt_match:
            youtube_url = yt_match.group(1)
            conv_type = "CHAT_WITH_YOUTUBE_VIDEO"

    # Création de session persistante (PDF, YouTube)
    if conv_type in ["CHAT_WITH_PDF", "CHAT_WITH_YOUTUBE_VIDEO"]:
        session_id = _create_session(api_key, model_name, conv_type, file_ids, youtube_url)

    return {
        "type": conv_type,
        "session_id": session_id,
        "image_paths": image_paths,
        "prompt_object": None
    }

def _create_session(api_key, model, conv_type, file_ids, youtube_url):
    """Crée une session avec le préfixe n8n_ pour le traçage infra."""
    try:
        return create_1min_conversation(
            api_key=api_key,
            model=model,
            conv_type=conv_type,
            title=f"n8n_{conv_type}",
            file_ids=file_ids,
            youtube_url=youtube_url
        )
    except Exception as e:
        logger.error(f"DOMAIN | Failed to create session: {e}")
        return None