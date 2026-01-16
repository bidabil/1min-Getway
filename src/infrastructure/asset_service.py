import requests
import uuid
import base64
from io import BytesIO

def upload_image_to_1min(item, headers, asset_url):
    """
    Prend un item de message (OpenAI format), traite l'image 
    et l'upload sur 1min.ai. Retourne l'image_path.
    """
    image_url_data = item['image_url']['url']
    
    if image_url_data.startswith("data:image/png;base64,"):
        base64_image = image_url_data.split(",")[1]
        binary_data = base64.b64decode(base64_image)
    else:
        # Téléchargement depuis une URL externe
        response = requests.get(image_url_data)
        response.raise_for_status()
        binary_data = BytesIO(response.content)

    files = {
        'asset': (f"relay_{uuid.uuid4()}", binary_data, 'image/png')
    }
    
    asset_response = requests.post(asset_url, files=files, headers=headers)
    asset_response.raise_for_status()
    
    return asset_response.json()['fileContent']['path']