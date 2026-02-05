import logging
import socket

import requests
from flask import Response, jsonify, make_response, request
from waitress import serve

# Import centralisé depuis le package src
from src import (
    ALL_ONE_MIN_AVAILABLE_MODELS,
    ONE_MIN_API_URL,
    ONE_MIN_CONVERSATION_API_STREAMING_URL,
    PERMIT_MODELS_FROM_SUBSET_ONLY,
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS,
    app,
    calculate_token,
    format_conversation_history,
    get_error_response,
    get_formatted_models_list,
    handle_options_request,
    limiter,
    logger,
    set_response_headers,
    stream_response,
    transform_response,
)

# Import de l'orchestrateur
from src.application.orchestrator import resolve_conversation_context


@app.route("/v1/models", methods=["GET"])
@limiter.limit("20 per minute")
def list_models():
    """
    Expose la liste des modèles disponibles au format OpenAI.
    """
    # FIX: Passage des arguments requis pour la validation du pipeline
    models = get_formatted_models_list(
        all_models=ALL_ONE_MIN_AVAILABLE_MODELS,
        permit_subset_only=PERMIT_MODELS_FROM_SUBSET_ONLY,
        subset_models=SUBSET_OF_ONE_MIN_PERMITTED_MODELS,
    )
    return jsonify({"object": "list", "data": models}), 200


@app.route("/v1/chat/completions", methods=["POST", "OPTIONS"])
@limiter.limit("500 per minute")
def conversation():
    """
    Endpoint principal compatible OpenAI Chat Completions.
    """
    if request.method == "OPTIONS":
        return handle_options_request()

    # --- 1. Authentification Hybride (Bearer + API-KEY) ---
    api_key = request.headers.get("API-KEY") or (
        request.headers.get("Authorization", "").replace("Bearer ", "")
        if "Authorization" in request.headers
        else None
    )

    if not api_key:
        logger.warning("AUTH | Tentative d'accès sans clé API valide.")
        return get_error_response(1021)

    # --- 2. Extraction des données ---
    request_data = request.get_json(silent=True) or {}
    messages = request_data.get("messages", [])
    model_name = request_data.get("model", "gpt-4o")
    is_stream = request_data.get("stream", False)

    if not messages:
        return get_error_response(1412)

    try:
        # --- 3. Orchestration & Résolution du Contexte ---
        context = resolve_conversation_context(api_key, model_name, messages, request_data)

        if not context or not context.get("session_id") or "prompt_object" not in context:
            logger.error(f"ORCHESTRATOR | Contexte invalide pour {model_name}")
            return get_error_response(500, model=model_name)

        # --- 4. Gestion de l'Historique ---
        history_list = messages[:-1] if len(messages) > 1 else []
        last_prompt_content = context.get("prompt_object", {}).get("prompt", "")

        history_text = format_conversation_history(history_list, last_prompt_content)
        prompt_token_count = calculate_token(history_text, model_name)

        # --- 5. Préparation du Payload ---
        payload = {
            "model": model_name,
            "type": context["type"],
            "conversationId": context["session_id"],
            "promptObject": context["prompt_object"],
        }
        payload["promptObject"]["prompt"] = history_text

        # --- 6. Headers avec API-KEY obligatoire pour 1min.ai ---
        headers = {
            "API-KEY": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # --- 7. Exécution de l'appel ---
        if not is_stream:
            logger.info(f"API_CALL | Mode: Normal | Model: {model_name} | Conv: {context['type']}")
            res = requests.post(ONE_MIN_API_URL, json=payload, headers=headers, timeout=60)
            res.raise_for_status()

            transformed = transform_response(res.json(), model_name, prompt_token_count)
            return set_response_headers(make_response(jsonify(transformed))), 200

        else:
            logger.info(f"API_CALL | Mode: Stream | Model: {model_name} | Conv: {context['type']}")
            res_stream = requests.post(
                ONE_MIN_CONVERSATION_API_STREAMING_URL, json=payload, headers=headers, stream=True
            )
            res_stream.raise_for_status()

            return set_response_headers(
                Response(
                    stream_response(res_stream, model_name, int(prompt_token_count)),
                    content_type="text/event-stream",
                )
            )

    except requests.exceptions.RequestException as re:
        logger.error(f"UPSTREAM_ERROR | Erreur API 1min.ai: {str(re)}")
        return get_error_response(500, model=model_name)
    except Exception as e:
        logger.error(f"FATAL_ERROR | Type: {type(e).__name__} | Msg: {str(e)}")
        return get_error_response(500, model=model_name)


@app.route("/")
def health():
    return "1min-Gateway is running", 200


if __name__ == "__main__":
    local_ip = socket.gethostbyname(socket.gethostname())
    logger.info(f"RUNNING | Gateway sur http://{local_ip}:5001")
    serve(app, host="0.0.0.0", port=5001, threads=8)
