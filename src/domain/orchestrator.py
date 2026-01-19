import re
from src import logger, upload_image_to_1min, ONE_MIN_ASSET_URL
from src.infrastructure.conversation_service import create_1min_conversation

def resolve_conversation_context(api_key, model_name, current_user_message, request_data=None):
    """
    Analyse le message et les métadonnées (request_data) pour déterminer le type 
    de conversation et préparer les sessions ou les outils de génération de contenu.
    """
    request_data = request_data or {}
    conv_type = "CHAT_WITH_AI"
    session_id = None
    image_paths = []
    file_ids = []
    youtube_url = None
    prompt_object = None

    # --- 1. DÉTECTION CONTENT GENERATORS (Explicite via n8n/Metadata) ---
    content_type = request_data.get('content_type')
    
    if content_type:
        # Configuration commune aux générateurs
        prompt_object = {
            "tone": request_data.get('tone', 'informative'),
            "language": request_data.get('language', 'French'),
            "prompt": current_user_message if isinstance(current_user_message, str) else ""
        }
        
        # Mapping vers les endpoints spécialisés de 1min.ai
        if content_type == "BLOG_ARTICLE":
            conv_type = "CONTENT_GENERATOR_BLOG_ARTICLE"
            prompt_object.update({
                "numberOfWord": request_data.get('words', 1000),
                "numberOfSection": request_data.get('sections', 5),
                "keywords": request_data.get('keywords', '')
            })
        elif content_type in ["LINKEDIN_POST", "INSTAGRAM_POST", "X_TWEET", "FACEBOOK_POST"]:
            conv_type = f"CONTENT_GENERATOR_{content_type}"
        elif content_type in ["LINKEDIN_COMMENT", "X_COMMENT"]:
            conv_type = f"CONTENT_GENERATOR_{content_type}"
            prompt_object["postContent"] = request_data.get('post_content', '')
        elif content_type == "EMAIL":
            conv_type = "CONTENT_GENERATOR_EMAIL"
            prompt_object["emailType"] = request_data.get('email_type', 'outreach')
        elif content_type == "ADVERTISEMENT":
            conv_type = "CONTENT_GENERATOR_ADVERTISEMENT"
            prompt_object["targetAudience"] = request_data.get('audience', 'general')

        # Si on est en mode générateur, on retourne immédiatement l'objet structuré
        if conv_type.startswith("CONTENT_GENERATOR"):
            return {
                "type": conv_type,
                "session_id": conv_type, # 1min.ai utilise souvent le type comme ID pour les générateurs
                "image_paths": [],
                "prompt_object": prompt_object
            }

    # --- 2. DÉTECTION MULTIMÉDIA (Format OpenAI: list de dicts) ---
    if isinstance(current_user_message, list):
        for item in current_user_message:
            if 'image_url' in item:
                path = upload_image_to_1min(item, api_key, ONE_MIN_ASSET_URL)
                if path:
                    image_paths.append(path)
                    conv_type = "CHAT_WITH_IMAGE"
            elif 'file_id' in item:
                file_ids.append(item['file_id'])
                conv_type = "CHAT_WITH_PDF"

    # --- 3. DÉTECTION YOUTUBE (Format OpenAI: string) ---
    if isinstance(current_user_message, str) and "youtube.com/watch" in current_user_message:
        yt_match = re.search(r'(https?://www.youtube.com/watch\?v=[^\s&]+)', current_user_message)
        if yt_match:
            youtube_url = yt_match.group(1)
            conv_type = "CHAT_WITH_YOUTUBE_VIDEO"

    # --- 4. CRÉATION DE SESSION (Obligatoire pour PDF et YouTube) ---
    if conv_type in ["CHAT_WITH_PDF", "CHAT_WITH_YOUTUBE_VIDEO"]:
        session_id = _create_session(api_key, model_name, conv_type, file_ids, youtube_url)

    return {
        "type": conv_type,
        "session_id": session_id,
        "image_paths": image_paths,
        "prompt_object": None
    }

def _create_session(api_key, model, conv_type, file_ids, youtube_url):
    """
    Délègue la création de la session au service d'infrastructure.
    """
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
        logger.error(f"DOMAIN | Failed to resolve session ID via infrastructure: {e}")
        return None