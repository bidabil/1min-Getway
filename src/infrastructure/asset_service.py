# src/infrastructure/asset_service.py

""" Module de gestion des ressources (assets) pour la Gateway 1min.
Gère le téléchargement, le décodage et l'upload d'images.
"""

import base64
import logging
import uuid
from io import BytesIO

import filetype
import requests

# Standardized logger
logger = logging.getLogger("1min-gateway.asset-service")
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB


def _decode_base64_image(image_data):
    """Décode une image en base64 et extrait son type MIME."""
    header, _, b64 = image_data.partition(",")
    if not b64:
        raise ValueError("Invalid data URI")

    # Correction du padding
    padding = len(b64) % 4
    if padding:
        b64 += "=" * (4 - padding)

    try:
        binary_data = base64.b64decode(b64)
    except Exception:
        binary_data = base64.urlsafe_b64decode(b64)

    mime_type = header.split(":", 1)[1].split(";", 1)[0] if ";" in header else None
    return binary_data, mime_type


def _download_external_image(url):
    """Télécharge une image avec une limite de taille stricte."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    response = requests.get(url, timeout=20, stream=True)
    response.raise_for_status()

    buf = bytearray()
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            buf.extend(chunk)
            if len(buf) > MAX_IMAGE_SIZE:
                raise ValueError("FILE_TOO_LARGE_413")

    return bytes(buf), response.headers.get("Content-Type")


def upload_image_to_1min(item, headers, asset_url):
    """Traite une image (Base64 ou URL) et l'uploade sur 1min.ai.

    Retourne le chemin interne de l'image.
    """
    # 1. Validation simplifiée (pourrait aussi être une fonction à part)
    if not isinstance(item, dict) or "image_url" not in item:
        raise ValueError("Invalid 'item' structure")

    auth = headers.get("Authorization", "")
    if not isinstance(headers, dict) or not auth.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")

    image_data = item["image_url"]["url"]

    try:
        # 2. Acquisition des données binaires
        if image_data.startswith("data:image"):
            binary_data, mime_type = _decode_base64_image(image_data)
        else:
            binary_data, mime_type = _download_external_image(image_data)

        # 3. Détection du type de fichier si nécessaire
        if not mime_type:
            kind = filetype.guess(binary_data)
            mime_type = kind.mime if kind else "image/png"

        # 4. Préparation du fichier
        ext = mime_type.split("/")[-1].split("+")[0]
        filename = f"gateway_{uuid.uuid4()}.{ext}"
        files = {"asset": (filename, BytesIO(binary_data), mime_type)}

        # 5. Upload final
        asset_response = requests.post(asset_url, files=files, headers=headers, timeout=30)
        asset_response.raise_for_status()

        body = asset_response.json()
        return body["fileContent"]["path"]

    except ValueError as e:
        if str(e) == "FILE_TOO_LARGE_413":
            logger.error("ASSET | Fichier trop volumineux (> 50MB)")
            # Relancer avec message clair
            raise ValueError("File size exceeds 50MB limit")
        else:
            logger.error("Failed to process image: %s", str(e))
            raise
    except Exception as e:
        logger.error("Failed to process image: %s", str(e))
        raise
