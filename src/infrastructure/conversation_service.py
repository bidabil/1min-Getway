import requests
from src import logger

def create_1min_conversation(api_key, model, conv_type="CHAT_WITH_AI", title="n8n Session", file_ids=None, youtube_url=None):
    """
    Service d'infrastructure : Gère l'appel brut à l'API Conversations de 1min.ai.
    Implémente les spécifications 2026 (API-KEY et types de conversations).
    """
    url = "https://api.1min.ai/api/conversations"
    
    headers = {
        'API-KEY': api_key,  # Authentification système requise pour cet endpoint
        'Content-Type': 'application/json'
    }
    
    # Construction du payload selon la doc 2026
    payload = {
        "type": conv_type,
        "title": title[:90],
        "model": model
    }
    
    # Ajout des paramètres optionnels selon le type
    if file_ids:
        payload["fileList"] = file_ids
        
    if youtube_url:
        payload["youtubeUrl"] = youtube_url

    try:
        logger.info(f"INFRA | Creating {conv_type} session for model {model}")
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        # Gestion des erreurs spécifique à la doc (401, 422, etc.)
        if response.status_code != 200:
            error_data = response.json()
            logger.error(f"INFRA | 1min.ai Error: {error_data.get('error', {}).get('message')}")
            response.raise_for_status()

        return response.json()['conversation']['uuid']
        
    except Exception as e:
        logger.error(f"INFRA | Failed to create conversation: {str(e)}")
        raise e