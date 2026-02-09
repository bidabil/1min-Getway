# src/routes.py
"""
Routes HTTP - Couche Présentation
Utilise les Use Cases pour la logique métier
"""

import logging

import requests
from flask import Response, jsonify, make_response, request

from .adapters.openai_adapter import stream_response, transform_response
from .application.use_cases import Failure, Success
from .config import ONE_MIN_FEATURE_API_URL, RATELIMIT_DEFAULT
from .container import container
from .domain.ports import ChatRequest
from .infrastructure.error_service import get_error_response
from .infrastructure.network_service import handle_options_request, set_response_headers

logger = logging.getLogger("1min-gateway.routes")


def extract_api_key(req):
    """Extrait la clé API (API-KEY ou Bearer)"""
    api_key = req.headers.get("API-KEY")
    if api_key:
        return api_key
    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def register_routes(app, limiter):
    """Enregistre les routes Flask"""

    @app.route("/v1/chat/completions", methods=["POST", "OPTIONS"])
    @limiter.limit(RATELIMIT_DEFAULT)
    def conversation():
        if request.method == "OPTIONS":
            return handle_options_request()

        # --- 1. AUTHENTIFICATION (Use Case) ---
        api_key = extract_api_key(request)
        auth_result = container.validate_api_key.execute(api_key)

        if isinstance(auth_result, Failure):
            return jsonify(
                {
                    "success": False,
                    "error": {"code": auth_result.error_code, "message": auth_result.message},
                }
            ), 401

        # --- 2. EXTRACTION DES DONNÉES ---
        request_data = request.get_json(silent=True) or {}

        chat_request = ChatRequest(
            api_key=api_key,
            model=request_data.get("model", "gpt-4o-mini"),
            messages=request_data.get("messages", []),
            stream=request_data.get("stream", False),
            extra_params=request_data,
        )

        # --- 3. EXÉCUTION DU USE CASE ---
        result = container.chat_completion.execute(chat_request)

        if isinstance(result, Failure):
            error_payload, status = get_error_response_from_failure(result)
            return jsonify({"success": False, "error": error_payload}), status

        context = result.data

        # --- 4. CALCUL DES TOKENS (Use Case) ---
        prompt_text = context.prompt_object.get("prompt", "")
        tokens_result = container.calculate_tokens.execute(prompt_text, chat_request.model)
        prompt_token_count = tokens_result.data if isinstance(tokens_result, Success) else 0

        # --- 5. APPEL API UPSTREAM ---
        payload = {
            "type": context.type,
            "model": chat_request.model,
            "promptObject": context.prompt_object,
        }
        if context.session_id:
            payload["conversationId"] = context.session_id

        headers = {"API-KEY": api_key, "Content-Type": "application/json"}

        try:
            if not chat_request.stream:
                res = requests.post(
                    ONE_MIN_FEATURE_API_URL, json=payload, headers=headers, timeout=120
                )
                res.raise_for_status()
                transformed = transform_response(res.json(), chat_request.model, prompt_token_count)
                return set_response_headers(make_response(jsonify(transformed))), 200
            else:
                streaming_url = f"{ONE_MIN_FEATURE_API_URL}?isStreaming=true"
                res_stream = requests.post(
                    streaming_url, json=payload, headers=headers, stream=True, timeout=180
                )
                res_stream.raise_for_status()
                return set_response_headers(
                    Response(
                        stream_response(res_stream, chat_request.model, prompt_token_count),
                        content_type="text/event-stream",
                    )
                )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 500
            error_payload, status = get_error_response(status_code)
            return jsonify({"success": False, "error": error_payload}), status

    @app.route("/")
    def health():
        return jsonify({"status": "ok", "architecture": "Clean + Use Cases"}), 200


def get_error_response_from_failure(failure: Failure):
    """Convertit un Failure en réponse d'erreur HTTP"""
    error_map = {
        "MODEL_NOT_FOUND": ({"code": failure.error_code, "message": failure.message}, 404),
        "INVALID_REQUEST": ({"code": failure.error_code, "message": failure.message}, 400),
        "UNAUTHORIZED": ({"code": failure.error_code, "message": failure.message}, 401),
        "CONTEXT_ERROR": ({"code": failure.error_code, "message": failure.message}, 500),
        "INTERNAL_ERROR": ({"code": failure.error_code, "message": failure.message}, 500),
    }
    return error_map.get(failure.error_code, ({"code": "UNKNOWN", "message": failure.message}, 500))
