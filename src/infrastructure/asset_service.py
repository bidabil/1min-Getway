#asset_service.py

import requests
import uuid
import base64
import logging
from io import BytesIO

# Standardized logger for the asset management layer
logger = logging.getLogger("1min-gateway.asset-service")

def upload_image_to_1min(item, headers, asset_url):
    """
    Processes an OpenAI-format image input (Base64 or URL) and uploads it 
    to 1min.ai's storage. Returns the internal image path.
    Strictly follows 2026 Authentication (Bearer).
    """
    image_url_data = item['image_url']['url']
    
    try:
        if image_url_data.startswith("data:image"):
            logger.debug("Processing Base64 image data.")
            base64_image = image_url_data.split(",")[1]
            binary_data = base64.b64decode(base64_image)
        else:
            logger.debug(f"Downloading external image: {image_url_data[:50]}...")
            response = requests.get(image_url_data, timeout=20)
            response.raise_for_status()
            binary_data = response.content

        filename = f"gateway_{uuid.uuid4()}.png"
        files = {
            'asset': (filename, BytesIO(binary_data), 'image/png')
        }
        
        # headers passed here MUST contain 'Authorization': 'Bearer <key>'
        logger.debug(f"Uploading file to 1min.ai Asset API: {filename}")
        asset_response = requests.post(
            asset_url, 
            files=files, 
            headers=headers, 
            timeout=30
        )
        asset_response.raise_for_status()
        
        path = asset_response.json()['fileContent']['path']
        logger.info(f"Asset upload complete. Internal path: {path}")
        return path

    except requests.exceptions.Timeout:
        logger.error("TIMEOUT | Image processing (download/upload) exceeded the limit.")
        raise
    except Exception as e:
        logger.error(f"ERROR | Failed to process or upload image: {str(e)}")
        raise