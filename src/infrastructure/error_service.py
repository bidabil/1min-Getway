# infrastructure/error_service.py

from flask import jsonify
import logging

# Standardized logger for the error management layer
logger = logging.getLogger("1min-gateway.error-service")

def get_error_response(code, model=None, key=None):
    """
    Handles errors and returns them in the OpenAI-compatible structured JSON format.
    Centralizing this logic keeps the main controller clean and ensures consistent responses.
    """
    error_codes = {
        1002: {
            "message": f"The model '{model}' does not exist.", 
            "type": "invalid_request_error", 
            "param": None, 
            "code": "model_not_found", 
            "http_code": 404
        },
        1020: {
            "message": "Incorrect API key provided. You can find your API key at https://app.1min.ai/api.", 
            "type": "authentication_error", 
            "param": None, 
            "code": "invalid_api_key", 
            "http_code": 401
        },
        1021: {
            "message": "Invalid Authentication provided.", 
            "type": "invalid_request_error", 
            "param": None, 
            "code": None, 
            "http_code": 401
        },
        1212: {
            "message": "Incorrect Endpoint. Please use the /v1/chat/completions endpoint.", 
            "type": "invalid_request_error", 
            "param": None, 
            "code": "model_not_supported", 
            "http_code": 400
        },
        1044: {
            "message": f"The model '{model}' does not support this type of input (e.g. image).", 
            "type": "invalid_request_error", 
            "param": None, 
            "code": "model_not_supported", 
            "http_code": 400
        },
        1412: {
            "message": "No messages provided in the request body.", 
            "type": "invalid_request_error", 
            "param": "messages", 
            "code": "invalid_request_error", 
            "http_code": 400
        },
        1423: {
            "message": "The last message provided has no content.", 
            "type": "invalid_request_error", 
            "param": "messages", 
            "code": "invalid_request_error", 
            "http_code": 400
        },
        1405: {
            "message": "Method Not Allowed.", 
            "type": "invalid_request_error", 
            "param": None, 
            "code": None, 
            "http_code": 405
        },
        500: {
            "message": "Internal Server Error. Please check the 1min-Gateway logs.", 
            "type": "api_error", 
            "param": None, 
            "code": "internal_error", 
            "http_code": 500
        }
    }
    
    # Fallback for undefined error codes
    raw_error = error_codes.get(code, {
        "message": "An unknown error occurred.", 
        "type": "unknown_error", 
        "param": None, 
        "code": None, 
        "http_code": 400
    })
    
    http_status = raw_error.get("http_code", 400)
    
    # Prepare the payload for the client by removing internal fields (like http_code)
    error_payload = {k: v for k, v in raw_error.items() if k != "http_code"}
    
    # Audit Log: Providing context for quick debugging
    logger.error(
        f"API_ERROR | Code: {code} | Status: {http_status} | "
        f"Msg: {error_payload['message']} | Model: {model}"
    )
    
    return jsonify({"error": error_payload}), http_status