# infrastructure/error_service.py
"""
Service de gestion des erreurs pour la Gateway 1min.AI
Format conforme à la documentation officielle : https://docs.1min.ai
"""

import logging

logger = logging.getLogger("1min-gateway.error-service")


def get_error_response(code, model=None, key=None):
    """
    Gère les erreurs et les retourne au format JSON structuré.

    Format conforme à la documentation 1min.AI :
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Description de l'erreur"
        }
    }
    """
    error_codes = {
        # Erreurs de validation
        1002: {
            "code": "MODEL_NOT_FOUND",
            "message": f"The model '{model}' does not exist or is not available.",
            "http_code": 404,
        },
        1044: {
            "code": "MODEL_NOT_SUPPORTED",
            "message": f"The model '{model}' does not support this type of input.",
            "http_code": 400,
        },
        1212: {
            "code": "INVALID_ENDPOINT",
            "message": "Incorrect Endpoint. Please use the /v1/chat/completions endpoint.",
            "http_code": 400,
        },
        1412: {
            "code": "INVALID_REQUEST",
            "message": "No messages provided in the request body.",
            "http_code": 400,
        },
        1423: {
            "code": "INVALID_REQUEST",
            "message": "The last message provided has no content.",
            "http_code": 400,
        },
        # Erreurs d'authentification (selon doc 1min.ai)
        1020: {
            "code": "UNAUTHORIZED",
            "message": "Invalid or missing API key. Get your key at https://app.1min.ai/api",
            "http_code": 401,
        },
        1021: {
            "code": "UNAUTHORIZED",
            "message": "Invalid or missing API key.",
            "http_code": 401,
        },
        # Erreurs de permission (selon doc)
        403: {
            "code": "FORBIDDEN",
            "message": "Insufficient permissions or quota exceeded.",
            "http_code": 403,
        },
        # Erreurs de méthode
        1405: {
            "code": "METHOD_NOT_ALLOWED",
            "message": "Method Not Allowed.",
            "http_code": 405,
        },
        # Erreurs de payload (selon doc Asset API)
        413: {
            "code": "PAYLOAD_TOO_LARGE",
            "message": "File size exceeds maximum limit of 50MB.",
            "http_code": 413,
        },
        # Erreurs de validation entité (selon doc)
        422: {
            "code": "UNPROCESSABLE_ENTITY",
            "message": "Invalid file IDs or unsupported model.",
            "http_code": 422,
        },
        # Rate limit (selon doc : 180 req/min)
        429: {
            "code": "TOO_MANY_REQUESTS",
            "message": "Rate limit exceeded (180 requests per minute).",
            "http_code": 429,
        },
        # Erreurs serveur
        500: {
            "code": "INTERNAL_ERROR",
            "message": "Internal Server Error. Please check the gateway logs.",
            "http_code": 500,
        },
    }

    # Fallback pour codes non définis
    raw_error = error_codes.get(
        code,
        {
            "code": "UNKNOWN_ERROR",
            "message": "An unknown error occurred.",
            "http_code": 400,
        },
    )

    http_status = raw_error.get("http_code", 400)

    # Format conforme à la doc 1min.ai
    error_payload = {
        "code": raw_error["code"],
        "message": raw_error["message"],
    }

    # Log d'audit
    logger.error(
        f"API_ERROR | Code: {code} | Status: {http_status} | "
        f"Msg: {error_payload['message']} | Model: {model}"
    )

    return error_payload, http_status
