from flask import jsonify
import logging

# On récupère le logger configuré dans factory.py
logger = logging.getLogger("1min-relay")

def ERROR_HANDLER(code, model=None, key=None):
    """
    Gère les erreurs au format OpenAI-Structured.
    Centralisé pour éviter de polluer le fichier principal.
    """
    error_codes = {
        1002: {"message": f"The model {model} does not exist.", "type": "invalid_request_error", "param": None, "code": "model_not_found", "http_code": 400},
        1020: {"message": f"Incorrect API key provided: {key}. You can find your API key at https://app.1min.ai/api.", "type": "authentication_error", "param": None, "code": "invalid_api_key", "http_code": 401},
        1021: {"message": "Invalid Authentication", "type": "invalid_request_error", "param": None, "code": None, "http_code": 401},
        1212: {"message": f"Incorrect Endpoint. Please use the /v1/chat/completions endpoint.", "type": "invalid_request_error", "param": None, "code": "model_not_supported", "http_code": 400},
        1044: {"message": f"This model does not support image inputs.", "type": "invalid_request_error", "param": None, "code": "model_not_supported", "http_code": 400},
        1412: {"message": f"No message provided.", "type": "invalid_request_error", "param": "messages", "code": "invalid_request_error", "http_code": 400},
        1423: {"message": f"No content in last message.", "type": "invalid_request_error", "param": "messages", "code": "invalid_request_error", "http_code": 400},
        1405: {"message": "Method Not Allowed", "type": "invalid_request_error", "param": None, "code": None, "http_code": 405},
    }
    
    # Récupération de l'erreur ou message par défaut
    raw_error = error_codes.get(code, {"message": "Unknown error", "type": "unknown_error", "param": None, "code": None, "http_code": 400})
    
    # Extraction du code HTTP (on ne veut pas l'envoyer dans le JSON de réponse)
    http_status = raw_error.get("http_code", 400)
    error_payload = {k: v for k, v in raw_error.items() if k != "http_code"}
    
    logger.error(f"An error has occurred while processing the user's request. Error code: {code}")
    return jsonify({"error": error_payload}), http_status