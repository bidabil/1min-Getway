# infrastructure/asset_service.py

import requests
import uuid
import base64
import logging
from io import BytesIO
import imghdr

# Standardized logger for the asset management layer
logger = logging.getLogger("1min-gateway.asset-service")
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

def upload_image_to_1min(item, headers, asset_url):
    """
    Processes an OpenAI-format image input (Base64 or URL) and uploads it 
    to 1min.ai's storage. Returns the internal image path.
    Strictly follows 2026 Authentication (Bearer).
    """
    # Validate inputs
    if not isinstance(item, dict) or 'image_url' not in item or 'url' not in item['image_url']:
        logger.error("Invalid 'item' structure passed to upload_image_to_1min")
        raise ValueError("Invalid 'item' structure: missing image_url.url")
    if not isinstance(headers, dict) or 'Authorization' not in headers or not headers['Authorization'].startswith('Bearer '):
        logger.error("Missing or invalid Authorization header for asset upload")
        raise ValueError("Missing or invalid Authorization header")
    
    image_url_data = item['image_url']['url']
    
    try:
        mime_type = None
        # base64 data URI
        if image_url_data.startswith("data:image"):
            logger.debug("Processing Base64 image data.")
            # data:[<mediatype>][;base64],<data>
            header, _, b64 = image_url_data.partition(',')
            if not b64:
                logger.error("Invalid data URI for image")
                raise ValueError("Invalid data URI")
            # fix padding if necessary
            padding = len(b64) % 4
            if padding:
                b64 += '=' * (4 - padding)
            try:
                binary_data = base64.b64decode(b64)
            except Exception as be:
                logger.error(f"Base64 decode error: {be}")
                # try URL-safe decode as fallback
                binary_data = base64.urlsafe_b64decode(b64)
            # parse MIME from header: data:image/png;base64
            if ';' in header:
                mime_type = header.split(':', 1)[1].split(';', 1)[0]
        else:
            logger.debug(f"Downloading external image: {image_url_data[:50]}...")
            # ensure scheme
            if not image_url_data.startswith(('http://', 'https://')):
                image_url_data = 'https://' + image_url_data
            response = requests.get(image_url_data, timeout=20, stream=True)
            response.raise_for_status()
            # stream read with size limit
            buf = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    buf.extend(chunk)
                    if len(buf) > MAX_IMAGE_SIZE:
                        logger.error("Downloaded image exceeds maximum allowed size")
                        raise ValueError("Image too large")
            binary_data = bytes(buf)
            mime_type = response.headers.get('Content-Type')
        
        # try to detect image type if MIME not known
        if not mime_type:
            detected = imghdr.what(None, h=binary_data)
            if detected:
                mime_type = f"image/{detected}"
            else:
                # fallback
                mime_type = "image/png"
        ext = mime_type.split('/')[-1].split('+')[0]
        filename = f"gateway_{uuid.uuid4()}.{ext}"
        files = {
            'asset': (filename, BytesIO(binary_data), mime_type)
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
        
        try:
            body = asset_response.json()
            path = body['fileContent']['path']
        except Exception as je:
            logger.error(f"Asset upload returned unexpected body: {je}")
            raise
        logger.info(f"Asset upload complete. Internal path: {path}")
        return path

    except requests.exceptions.Timeout:
        logger.error("TIMEOUT | Image processing (download/upload) exceeded the limit.")
        raise
    except Exception as e:
        logger.error(f"ERROR | Failed to process or upload image: {str(e)}")
        raise