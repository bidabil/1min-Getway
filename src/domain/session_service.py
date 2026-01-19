import re
from src.infrastructure.conversation_service import create_1min_conversation

def resolve_session_params(api_key, model, current_message):
    """
    Analyse le message et retourne le type de conv, l'ID de session 
    et les assets associés.
    """
    conv_type = "CHAT_WITH_AI"
    session_id = None
    file_ids = []
    youtube_url = None

    # Logique de détection (extraite du main)
    if isinstance(current_message, list):
        # ... logique image/pdf ...
        pass
    
    if isinstance(current_message, str):
        yt_match = re.search(r'(https?://www.youtube.com/watch\?v=[^\s]+)', current_message)
        if yt_match:
            youtube_url = yt_match.group(1)
            conv_type = "CHAT_WITH_YOUTUBE_VIDEO"

    # Si besoin de session réelle
    if conv_type in ["CHAT_WITH_PDF", "CHAT_WITH_YOUTUBE_VIDEO"]:
        session_id = create_1min_conversation(api_key, model, conv_type, file_ids, youtube_url)
    
    return conv_type, session_id