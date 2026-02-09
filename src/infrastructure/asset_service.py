"""Service de gestion des assets (images, fichiers)
Aligné sur la documentation officielle Asset API
Documentation : https://docs.1min.ai/asset-api
"""

import base64
import logging
import uuid
from io import BytesIO

import filetype
import requests

logger = logging.getLogger("1min-gateway.asset-service")

# Limite selon documentation : 50MB
MAX_IMAGE_SIZE = 50 * 1024 * 1024


def _decode_base64_image(image_data):
    """Décode une image en base64"""
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
    """Télécharge une image avec limite de taille stricte"""
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
    """
    Upload une image sur l'API Asset de 1min.ai

    Documentation : https://docs.1min.ai/asset-api

    Args:
        item: Dict avec structure {"image_url": {"url": "..."}}
        headers: Headers d'authentification (API-KEY: votre_clé)
        asset_url: URL de l'endpoint Asset API

    Returns:
        str: Chemin de l'image uploadée (ex: "images/2024_09_30_...")

    Raises:
        ValueError: Si l'item est invalide ou le fichier trop volumineux
        requests.HTTPError: Si l'upload échoue
    """

    # Validation de l'input
    if not isinstance(item, dict) or "image_url" not in item:
        raise ValueError("Invalid 'item' structure - Expected {'image_url': {'url': '...'}}")

    api_key = headers.get("API-KEY", "")
    if not api_key:
        raise ValueError("Missing API-KEY header")

    image_data = item["image_url"]["url"]

    try:
        # Acquisition des données binaires
        if image_data.startswith("data:image"):
            binary_data, mime_type = _decode_base64_image(image_data)
        else:
            binary_data, mime_type = _download_external_image(image_data)

        # Détection du type de fichier
        if not mime_type:
            kind = filetype.guess(binary_data)
            mime_type = kind.mime if kind else "image/png"

        # Préparation du fichier pour upload
        ext = mime_type.split("/")[-1].split("+")[0]
        filename = f"gateway_{uuid.uuid4()}.{ext}"

        # Selon documentation : le paramètre s'appelle "asset"
        files = {"asset": (filename, BytesIO(binary_data), mime_type)}

        # Headers pour upload
        # Documentation 1min.ai : Utiliser "API-KEY" header
        upload_headers = {
            "API-KEY": api_key,
        }

        # Upload
        logger.info(f"ASSET | Upload de {filename} ({len(binary_data)} bytes)")

        asset_response = requests.post(
            asset_url,
            files=files,
            headers=upload_headers,
            timeout=30,
        )
        asset_response.raise_for_status()

        # Extraction du path selon structure documentée
        # Référence : https://docs.1min.ai/asset-api#response-payload
        body = asset_response.json()

        # Format 1min.ai : "asset.key" est le chemin
        path = body.get("asset", {}).get("key")
        if not path:
            # Fallback pour compatibilité
            path = body.get("fileContent", {}).get("path")

        if not path:
            logger.error(f"ASSET | Réponse invalide: {body}")
            raise ValueError("Invalid API response - missing 'path' or 'key'")

        logger.info(f"ASSET | Upload réussi: {path}")
        return path

    except ValueError as e:
        if str(e) == "FILE_TOO_LARGE_413":
            logger.error("ASSET | Fichier > 50MB")
            raise ValueError("File size exceeds 50MB limit") from e
        else:
            logger.error(f"ASSET | Erreur de validation: {e!s}")
            raise

    except requests.HTTPError as http_err:
        logger.error(f"ASSET | Erreur HTTP {http_err.response.status_code}: {http_err}")
        raise

    except Exception as e:
        logger.error(f"ASSET | Erreur inattendue: {e!s}")
        raise
