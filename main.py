# main.py

import requests
import socket
import logging
from flask import request, jsonify, make_response, Response
from waitress import serve

from src import (
    app, logger, limiter, get_error_response,
    format_conversation_history, get_formatted_models_list,
    handle_options_request, set_response_headers,
    transform_response, stream_response,
    ONE_MIN_API_URL, ONE_MIN_CONVERSATION_API_STREAMING_URL,
    ALL_ONE_MIN_AVAILABLE_MODELS, calculate_token
)
from src.application.orchestrator import resolve_conversation_context

@app.route('/v1/models', methods=['GET'])
@limiter.limit("20 per minute")
def list_models():
    models = get_formatted_models_list()
    return jsonify({"object": "list", "data": models}), 200

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
@limiter.limit("500 per minute")
def conversation():
    if request.method == 'OPTIONS':
        return handle_options_request()

    api_key = request.headers.get('API-KEY') or \
              (request.headers.get('Authorization', '').replace('Bearer ', '') 
               if 'Authorization' in request.headers else None)
    
    if not api_key:
        logger.warning("AUTH | Tentative d'accès sans clé API valide.")
        return get_error_response(1021)
    
    request_data = request.get_json(silent=True) or {}
    messages = request_data.get('messages', [])
    model_name = request_data.get('model', 'gpt-4o')
    is_stream = request_data.get('stream', False)

    if not messages:
        return get_error_response(1412)

    try:
        context = resolve_conversation_context(api_key, model_name, messages, request_data)
        
        if not context or not context.get("session_id") or "prompt_object" not in context:
            logger.error(f"ORCHESTRATOR | Contexte invalide reçu pour {model_name}")
            return get_error_response(500)
            
        history_list = messages[:-1] if len(messages) > 1 else []
        last_prompt_content = context.get("prompt_object", {}).get("prompt", "")
        
        history_text = format_conversation_history(history_list, last_prompt_content)
        prompt_token_count = calculate_token(history_text, model_name)
        
        payload = {
            "model": model_name,
            "type": context["type"],
            "conversationId": context["session_id"],
            "promptObject": context["prompt_object"]
        }
        payload["promptObject"]["prompt"] = history_text

        # --- FIX: Headers avec API-KEY pour l'appel final ---
        headers = {
            'API-KEY': api_key,
            'Authorization': f'Bearer {api_key}', 
            'Content-Type': 'application/json'
        }

        if not is_stream:
            logger.info(f"API_CALL | Mode: Normal | Model: {model_name} | Conv: {context['type']}")
            res = requests.post(ONE_MIN_API_URL, json=payload, headers=headers, timeout=60)
            res.raise_for_status()
            
            transformed = transform_response(res.json(), model_name, prompt_token_count)
            return set_response_headers(make_response(jsonify(transformed))), 200
        
        else:
            logger.info(f"API_CALL | Mode: Stream | Model: {model_name} | Conv: {context['type']}")
            res_stream = requests.post(
                ONE_MIN_CONVERSATION_API_STREAMING_URL, 
                json=payload, 
                headers=headers, 
                stream=True
            )
            res_stream.raise_for_status()
            
            return set_response_headers(
                Response(
                    stream_response(res_stream, model_name, int(prompt_token_count)), 
                    content_type='text/event-stream'
                )
            )

    except requests.exceptions.RequestException as re:
        logger.error(f"UPSTREAM_ERROR | Erreur API 1min.ai: {str(re)}")
        return get_error_response(500, model=model_name)
    except Exception as e:
        logger.error(f"FATAL_ERROR | Type: {type(e).__name__} | Msg: {str(e)}")
        return get_error_response(500, model=model_name)

@app.route('/')
def health():
    return "1min-Gateway is running", 200

if __name__ == '__main__':
    local_ip = socket.gethostbyname(socket.gethostname())
    logger.info(f"RUNNING | Gateway sur http://{local_ip}:5001")
    serve(app, host='0.0.0.0', port=5001, threads=8)