from src import (
    app, logger, limiter, ERROR_HANDLER,
    format_conversation_history,
    get_formatted_models_list,
    upload_image_to_1min,
    request, jsonify, make_response, Response,
    AVAILABLE_MODELS, calculate_token,
    ONE_MIN_API_URL, ONE_MIN_CONVERSATION_API_URL,
    ONE_MIN_CONVERSATION_API_STREAMING_URL, ONE_MIN_ASSET_URL,
    vision_supported_models, image_generation_models,
    ALL_ONE_MIN_AVAILABLE_MODELS,
    PERMIT_MODELS_FROM_SUBSET_ONLY,
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS
)
import requests
import json
import os
import socket
import printedcolors
from waitress import serve

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        internal_ip = socket.gethostbyname(socket.gethostname())
        return "Congratulations! Your API is working! You can now make requests to the API.\n\nEndpoint: " + internal_ip + ':5001/v1'
    return ERROR_HANDLER(1405)  # Default return for any other methods
@app.route('/v1/models')
@limiter.limit("500 per minute")
def models():
    # On appelle le service en lui passant les variables de configuration
    models_data = get_formatted_models_list(
        ALL_ONE_MIN_AVAILABLE_MODELS, 
        PERMIT_MODELS_FROM_SUBSET_ONLY, 
        SUBSET_OF_ONE_MIN_PERMITTED_MODELS
    )
    
    # On retourne le résultat final
    return jsonify({"data": models_data, "object": "list"})

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
@limiter.limit("500 per minute")
def conversation():
    if request.method == 'OPTIONS':
        return handle_options_request()

    # 1. Authentification
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.error("Invalid Authentication")
        return ERROR_HANDLER(1021)
    
    api_key = auth_header.split(" ")[1]
    headers = {'API-KEY': api_key, 'Content-Type': 'application/json'}
    
    # 2. Préparation des données
    request_data = request.json
    messages = request_data.get('messages', [])
    model_name = request_data.get('model', 'mistral-nemo')

    if not messages:
        return ERROR_HANDLER(1412)

    # 3. Formatage de l'historique (Service Domain)
    all_messages = format_conversation_history(messages, request_data.get('new_input', ''))
    
    # 4. Gestion de la Vision (Service Infrastructure)
    image = False
    image_paths = []
    user_content = messages[-1].get('content')

    if isinstance(user_content, list):
        for item in user_content:
            if 'image_url' in item:
                if model_name not in vision_supported_models:
                    return ERROR_HANDLER(1044, model_name)
                try:
                    # Utilisation du service extrait
                    path = upload_image_to_1min(item, headers, ONE_MIN_ASSET_URL)
                    image_paths.append(path)
                    image = True
                except Exception as e:
                    logger.error(f"Asset Upload Error: {str(e)[:100]}")
                    return ERROR_HANDLER(500) # Ou gestion spécifique

    # 5. Validation du modèle et Tokens
    prompt_token = calculate_token(str(all_messages))
    if PERMIT_MODELS_FROM_SUBSET_ONLY and model_name not in AVAILABLE_MODELS:
        return ERROR_HANDLER(1002, model_name)
    
    logger.debug(f"Processing {prompt_token} tokens with model {model_name}")

    # 6. Construction du Payload 1min.ai
    payload = {
        "model": model_name,
        "promptObject": {
            "prompt": all_messages,
            "isMixed": False,
        }
    }
    
    if image:
        payload["type"] = "CHAT_WITH_IMAGE"
        payload["promptObject"]["imageList"] = image_paths
    else:
        payload["type"] = "CHAT_WITH_AI"
        payload["promptObject"]["webSearch"] = False

    # 7. Exécution de la requête (Streaming ou Standard)
    is_streaming = request_data.get('stream', False)

    if not is_streaming:
        response = requests.post(ONE_MIN_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        transformed = transform_response(response.json(), request_data, prompt_token)
        flask_res = make_response(jsonify(transformed))
        set_response_headers(flask_res)
        return flask_res, 200
    
    else:
        res_stream = requests.post(
            ONE_MIN_CONVERSATION_API_STREAMING_URL, 
            data=json.dumps(payload), 
            headers=headers, 
            stream=True
        )
        
        if res_stream.status_code != 200:
            return ERROR_HANDLER(res_stream.status_code) if res_stream.status_code == 401 else ERROR_HANDLER(1020)

        return Response(
            stream_response(res_stream, request_data, model_name, int(prompt_token)), 
            content_type='text/event-stream'
        )

@app.route('/v1/images/generations', methods=['POST', 'OPTIONS'])
@limiter.limit("100 per minute")
def generate_images():
    if request.method == 'OPTIONS':
        return handle_options_request()

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.error("Invalid Authentication")
        return ERROR_HANDLER(1021)

    api_key = auth_header.split(" ")[1]
    headers = {
        'API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    request_data = request.json
    prompt = request_data.get('prompt')
    if not prompt:
        return ERROR_HANDLER(1412)  # No prompt provided

    num_images = request_data.get('n', 1)
    image_size = request_data.get('size', "1024x1024")
    model = request_data.get('model', 'black-forest-labs/flux-schnell')
    if not model in image_generation_models:
        return ERROR_HANDLER(1044, model)

    payload = {
        "type": "IMAGE_GENERATOR",
        "model": model,
        "promptObject": {
            "prompt": prompt,
            "n": num_images,
            "size": image_size
        }
    }

    try:
        logger.debug("Image Generation Requested.")
        response = requests.post(ONE_MIN_API_URL + "?isStreaming=false", json=payload, headers=headers)
        response.raise_for_status()
        one_min_response = response.json()

        image_urls = one_min_response['aiRecord']['aiRecordDetail']['resultObject']
        transformed_response = {
            "created": int(time.time()),
            "data": [{"url": url} for url in image_urls]
        }

        return jsonify(transformed_response), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Image generation failed: {str(e)}")
        return ERROR_HANDLER(1044)  # Handle image generation error

if __name__ == '__main__':
    internal_ip = socket.gethostbyname(socket.gethostname())
    response = requests.get('https://api.ipify.org')
    public_ip = response.text
    logger.info(f"""{printedcolors.Color.fg.lightcyan}  
Server is ready to serve at:
Internal IP: {internal_ip}:5001
Public IP: {public_ip} (only if you've setup port forwarding on your router.)
Enter this url to OpenAI clients supporting custom endpoint:
{internal_ip}:5001/v1
If does not work, try:
{internal_ip}:5001/v1/chat/completions
{printedcolors.Color.reset}""")
    serve(app, host='0.0.0.0', port=5001, threads=6) # Thread has a default of 4 if not specified. We use 6 to increase performance and allow multiple requests at once.