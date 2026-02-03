# infrastructure/one_min_client.py
import requests
import logging

logger = logging.getLogger("1min-gateway.one-min-client")
def create_1min_conversation(api_key, model, conv_type="CHAT_WITH_AI", title="n8n Session", file_ids=None, youtube_url=None, prompt_object=None):
    """
    Gère l'appel à /api/conversations pour obtenir un UUID de session.
    """
    url = "https://api.1min.ai/api/conversations"
    
    headers = {
        'API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "type": conv_type,
        "title": title[:90],
        "model": model
    }
    
    if prompt_object: payload["promptObject"] = prompt_object
    if file_ids: payload["fileList"] = file_ids
    if youtube_url: payload["youtubeUrl"] = youtube_url

    try:
        logger.info(f"INFRA | Création de conversation : {conv_type}")
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        # Si l'API renvoie une erreur (ex: 401, 400)
        if response.status_code != 200:
            logger.error(f"INFRA | 1min.ai API Error: {response.text}")
            return None

        data = response.json()
        
        # Extraction sécurisée de l'UUID selon la doc
        return data.get('conversation', {}).get('uuid')
        
    except Exception as e:
        logger.error(f"INFRA | Erreur fatale lors de l'appel : {str(e)}")
        return None