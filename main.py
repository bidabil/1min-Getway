from src import (
    app, logger, limiter, get_error_response,
    format_conversation_history, get_formatted_models_list,
    handle_options_request, set_response_headers,
    transform_response, stream_response,
    format_image_generation_response,
    request, jsonify, make_response, Response,
    AVAILABLE_MODELS, calculate_token,
    ONE_MIN_API_URL, ONE_MIN_CONVERSATION_API_STREAMING_URL,
    VISION_SUPPORTED_MODELS, IMAGE_GENERATION_MODELS,
    ALL_ONE_MIN_AVAILABLE_MODELS, PERMIT_MODELS_FROM_SUBSET_ONLY,
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS
)
from src.domain.orchestrator import resolve_conversation_context
import requests, socket, printedcolors
from waitress import serve

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        ip = socket.gethostbyname(socket.gethostname())
        return f"1min-Gateway is running!\n\nEndpoint: http://{ip}:5001/v1"
    return get_error_response(1405)

@app.route('/v1/models', methods=['GET'])
@limiter.limit("500 per minute")
def models():
    data = get_formatted_models_list(ALL_ONE_MIN_AVAILABLE_MODELS, PERMIT_MODELS_FROM_SUBSET_ONLY, SUBSET_OF_ONE_MIN_PERMITTED_MODELS)
    return jsonify({"data": data, "object": "list"})

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
@limiter.limit("500 per minute")
def conversation():
    if request.method == 'OPTIONS': return handle_options_request()

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "): return get_error_response(1021)
    
    api_key = auth_header.split(" ")[1]
    request_data = request.json
    messages = request_data.get('messages', [])
    model_name = request_data.get('model', 'gpt-4o-mini')

    if not messages: return get_error_response(1412)

    # --- DÉLÉGATION À L'ORCHESTRATEUR ---
    context = resolve_conversation_context(api_key, model_name, messages[-1].get('content', ''))
    
    # --- PRÉPARATION DU PAYLOAD ---
    all_messages = format_conversation_history(messages[:-1], messages[-1].get('content', ''))
    prompt_token = calculate_token(all_messages, model_name)
    
    payload = {
        "model": model_name,
        "type": context["type"],
        "promptObject": {
            "prompt": all_messages,
            "isMixed": False,
            "webSearch": request_data.get('web_search', False)
        }
    }
    
    if context["session_id"]: payload["conversationId"] = context["session_id"]
    if context["image_paths"]: payload["promptObject"]["imageList"] = context["image_paths"]

    # --- EXECUTION ---
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    is_streaming = request_data.get('stream', False)
    
    try:
        if not is_streaming:
            timeout = 120 if "o1" in model_name or "research" in model_name else 45
            res = requests.post(ONE_MIN_API_URL, json=payload, headers=headers, timeout=timeout)
            res.raise_for_status()
            transformed = transform_response(res.json(), model_name, prompt_token)
            return set_response_headers(make_response(jsonify(transformed))), 200
        else:
            res_stream = requests.post(ONE_MIN_CONVERSATION_API_STREAMING_URL, json=payload, headers=headers, stream=True, timeout=45)
            return Response(stream_response(res_stream, model_name, int(prompt_token)), content_type='text/event-stream')
    except Exception as e:
        logger.error(f"API_ERROR: {e}")
        return get_error_response(500)

@app.route('/v1/images/generations', methods=['POST', 'OPTIONS'])
@limiter.limit("100 per minute")
def generate_images():
    if request.method == 'OPTIONS': return handle_options_request()
    auth_header = request.headers.get('Authorization')
    if not auth_header: return get_error_response(1021)
    api_key = auth_header.split(" ")[1]
    
    req_data = request.json
    payload = {
        "type": "IMAGE_GENERATOR",
        "model": req_data.get('model', 'black-forest-labs/flux-schnell'),
        "promptObject": { "prompt": req_data.get('prompt'), "n": req_data.get('n', 1), "aspect_width": 1, "aspect_height": 1 }
    }
    try:
        res = requests.post(ONE_MIN_API_URL, json=payload, headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, timeout=60)
        return jsonify(format_image_generation_response(res.json())), 200
    except Exception: return get_error_response(500)

if __name__ == '__main__':
    logger.info(f"{printedcolors.Color.fg.lightcyan}1min-Gateway Pro-Architecture ready on port 5001{printedcolors.Color.reset}")
    serve(app, host='0.0.0.0', port=5001, threads=6)