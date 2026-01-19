from src import (
    app, logger, limiter, get_error_response,
    format_conversation_history,
    get_formatted_models_list,
    upload_image_to_1min,
    handle_options_request,
    set_response_headers,
    transform_response,
    stream_response,
    format_image_generation_response,
    request, jsonify, make_response, Response,
    AVAILABLE_MODELS, calculate_token,
    ONE_MIN_API_URL, 
    ONE_MIN_CONVERSATION_API_STREAMING_URL, ONE_MIN_ASSET_URL,
    VISION_SUPPORTED_MODELS, IMAGE_GENERATION_MODELS,
    ALL_ONE_MIN_AVAILABLE_MODELS,
    PERMIT_MODELS_FROM_SUBSET_ONLY,
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS
)
import requests
import json
import socket
import printedcolors
from waitress import serve

@app.route('/', methods=['GET', 'POST'])
def index():
    """Health check endpoint to verify API status."""
    if request.method == 'GET':
        internal_ip = socket.gethostbyname(socket.gethostname())
        return f"1min-Gateway is running!\n\nEndpoint: http://{internal_ip}:5001/v1"
    return get_error_response(1405)

@app.route('/v1/models', methods=['GET'])
@limiter.limit("500 per minute")
def models():
    """Returns the filtered list of available models."""
    models_data = get_formatted_models_list(
        ALL_ONE_MIN_AVAILABLE_MODELS, 
        PERMIT_MODELS_FROM_SUBSET_ONLY, 
        SUBSET_OF_ONE_MIN_PERMITTED_MODELS
    )
    return jsonify({"data": models_data, "object": "list"})

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
@limiter.limit("500 per minute")
def conversation():
    """Relays chat completion requests to 1min.ai with OpenAI formatting."""
    if request.method == 'OPTIONS':
        return handle_options_request()

    # 1. Authentication Check (Strict Bearer Compliance 2026)
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return get_error_response(1021)
    
    api_key = auth_header.split(" ")[1]
    headers = {
        'Authorization': f'Bearer {api_key}', 
        'Content-Type': 'application/json'
    }
    
    # 2. Data Extraction
    request_data = request.json
    messages = request_data.get('messages', [])
    model_name = request_data.get('model', 'gpt-4o-mini')

    if not messages:
        return get_error_response(1412)

    # 3. Message Detection
    current_user_message = messages[-1].get('content', '')
    history = messages[:-1]

    # 4. Vision Handling
    image_paths = []
    has_image = False
    
    if isinstance(current_user_message, list):
        for item in current_user_message:
            if 'image_url' in item:
                if model_name not in VISION_SUPPORTED_MODELS:
                    return get_error_response(1044, model_name)
                try:
                    # Pass raw api_key: asset_service uses 'API-KEY' header per doc
                    path = upload_image_to_1min(item, api_key, ONE_MIN_ASSET_URL)
                    image_paths.append(path)
                    has_image = True
                except Exception as e:
                    logger.error(f"Vision Upload Failed: {str(e)[:100]}")
                    return get_error_response(500)

    # 5. History & Tokens
    all_messages = format_conversation_history(history, current_user_message)
    prompt_token = calculate_token(all_messages, model_name)
    
    if PERMIT_MODELS_FROM_SUBSET_ONLY and model_name not in AVAILABLE_MODELS:
        return get_error_response(1002, model_name)
    
    # 6. Payload Preparation (Strict promptObject)
    payload = {
        "model": model_name,
        "promptObject": {
            "prompt": all_messages,
            "isMixed": False,
            "webSearch": request_data.get('web_search', False),
            "numOfSite": 1,
            "maxWord": 500
        },
        "type": "CHAT_WITH_IMAGE" if has_image else "CHAT_WITH_AI"
    }
    
    if has_image:
        payload["promptObject"]["imageList"] = image_paths

    # 7. Execution
    is_streaming = request_data.get('stream', False)
    logger.info(f"REQ | Model: {model_name} | Stream: {is_streaming}")

    try:
        if not is_streaming:
            timeout_val = 120 if any(x in model_name for x in ["o1", "o3", "research", "reasoner"]) else 45
            response = requests.post(ONE_MIN_API_URL, json=payload, headers=headers, timeout=timeout_val)
            response.raise_for_status()
            
            transformed = transform_response(response.json(), model_name, prompt_token)
            return set_response_headers(make_response(jsonify(transformed))), 200
        else:
            res_stream = requests.post(
                ONE_MIN_CONVERSATION_API_STREAMING_URL, 
                json=payload, 
                headers=headers, 
                stream=True,
                timeout=45
            )
            if res_stream.status_code != 200:
                return get_error_response(res_stream.status_code)

            return Response(
                stream_response(res_stream, model_name, int(prompt_token)), 
                content_type='text/event-stream'
            )
            
    except Exception as e:
        logger.error(f"API_ERROR | {str(e)}")
        return get_error_response(500)

@app.route('/v1/images/generations', methods=['POST', 'OPTIONS'])
@limiter.limit("100 per minute")
def generate_images():
    if request.method == 'OPTIONS':
        return handle_options_request()

    auth_header = request.headers.get('Authorization')
    if not auth_header: return get_error_response(1021)

    api_key = auth_header.split(" ")[1]
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    request_data = request.json
    prompt = request_data.get('prompt')
    model = request_data.get('model', 'black-forest-labs/flux-schnell')
    
    if model not in IMAGE_GENERATION_MODELS:
        return get_error_response(1044, model)

    payload = {
        "type": "IMAGE_GENERATOR",
        "model": model,
        "promptObject": {
            "prompt": prompt,
            "n": request_data.get('n', 1),
            "aspect_width": 1,
            "aspect_height": 1
        }
    }

    try:
        response = requests.post(ONE_MIN_API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return jsonify(format_image_generation_response(response.json())), 200
    except Exception as e:
        logger.error(f"IMG_ERROR | {str(e)}")
        return get_error_response(500)

if __name__ == '__main__':
    internal_ip = socket.gethostbyname(socket.gethostname())
    logger.info(f"{printedcolors.Color.fg.lightcyan}1min-Gateway ready! http://{internal_ip}:5001/v1{printedcolors.Color.reset}")
    serve(app, host='0.0.0.0', port=5001, threads=6)