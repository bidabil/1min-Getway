import re
from src import logger, upload_image_to_1min, ONE_MIN_ASSET_URL
from src.infrastructure.conversation_service import create_1min_conversation

def resolve_conversation_context(api_key, model_name, current_user_message):
    """
    Analyse le message de l'utilisateur pour déterminer le type de conversation 
    et préparer les sessions (Image, PDF, YouTube).
    """
    conv_type = "CHAT_WITH_AI"
    session_id = None
    image_paths = []
    file_ids = []
    youtube_url = None

    # 1. Détection de contenu multimédia (Format OpenAI: list de dicts)
    if isinstance(current_user_message, list):
        for item in current_user_message:
            # Gestion des images
            if 'image_url' in item:
                path = upload_image_to_1min(item, api_key, ONE_MIN_ASSET_URL)
                if path:
                    image_paths.append(path)
                    conv_type = "CHAT_WITH_IMAGE"
            # Gestion des fichiers (ex: PDF envoyé via n8n)
            elif 'file_id' in item:
                file_ids.append(item['file_id'])
                conv_type = "CHAT_WITH_PDF"

    # 2. Détection YouTube dans le texte (Format OpenAI: string)
    if isinstance(current_user_message, str) and "youtube.com/watch" in current_user_message:
        # Regex robuste pour extraire l'URL propre sans paramètres de tracking
        yt_match = re.search(r'(https?://www.youtube.com/watch\?v=[^\s&]+)', current_user_message)
        if yt_match:
            youtube_url = yt_match.group(1)
            conv_type = "CHAT_WITH_YOUTUBE_VIDEO"

    # 3. Création de Session (Obligatoire pour PDF et YouTube selon doc 2026)
    if conv_type in ["CHAT_WITH_PDF", "CHAT_WITH_YOUTUBE_VIDEO"]:
        session_id = _create_session(api_key, model_name, conv_type, file_ids, youtube_url)

    return {
        "type": conv_type,
        "session_id": session_id,
        "image_paths": image_paths
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