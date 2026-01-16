from src import (
    app, logger, limiter, ERROR_HANDLER,
    format_conversation_history,
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
import time
import uuid
import json
import os
import base64
import socket
import printedcolors
from io import BytesIO
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
    # Dynamically create the list of models with additional fields
    models_data = []
    if not PERMIT_MODELS_FROM_SUBSET_ONLY:
        one_min_models_data = [
            {
                "id": model_name,
                "object": "model",
                "owned_by": "1minai",
                "created": 1727389042
            }
            for model_name in ALL_ONE_MIN_AVAILABLE_MODELS
        ]
    else:
        one_min_models_data = [
            {"id": model_name, "object": "model", "owned_by": "1minai", "created": 1727389042}
            for model_name in SUBSET_OF_ONE_MIN_PERMITTED_MODELS
        ]
    models_data.extend(one_min_models_data)
    return jsonify({"data": models_data, "object": "list"})

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
@limiter.limit("500 per minute")
def conversation():
    if request.method == 'OPTIONS':
        return handle_options_request()
    image = False
    

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.error("Invalid Authentication")
        return ERROR_HANDLER(1021)
    
    api_key = auth_header.split(" ")[1]
    
    headers = {
        'API-KEY': api_key
    }
    
    request_data = request.json
    
    all_messages = format_conversation_history(request_data.get('messages', []), request_data.get('new_input', ''))

    messages = request_data.get('messages', [])
    if not messages:
        return ERROR_HANDLER(1412)

    user_input = messages[-1].get('content')
    if not user_input:
        return ERROR_HANDLER(1423)

    # Check if user_input is a list and combine text if necessary
    image = False
    if isinstance(user_input, list):
        image_paths = []
        for item in user_input:
            if 'text' in item:
                combined_text = '\n'.join(item['text'])
            try:
                if 'image_url' in item:
                    if request_data.get('model', 'mistral-nemo') not in vision_supported_models:
                        return ERROR_HANDLER(1044, request_data.get('model', 'mistral-nemo'))
                    if item['image_url']['url'].startswith("data:image/png;base64,"):
                        base64_image = item['image_url']['url'].split(",")[1]
                        binary_data = base64.b64decode(base64_image)
                    else:
                        binary_data = requests.get(item['image_url']['url'])
                        binary_data.raise_for_status()  # Raise an error for bad responses
                        binary_data = BytesIO(binary_data.content)
                    files = {
                        'asset': ("relay" + str(uuid.uuid4()), binary_data, 'image/png')
                    }
                    asset = requests.post(ONE_MIN_ASSET_URL, files=files, headers=headers)
                    asset.raise_for_status()  # Raise an error for bad responses
                    image_path = asset.json()['fileContent']['path']
                    image_paths.append(image_path)
                    image = True
            except Exception as e:
                print(f"An error occurred e:" + str(e)[:60])
                # Optionally log the error or return an appropriate response

        user_input = str(combined_text)

    prompt_token = calculate_token(str(all_messages))
    if PERMIT_MODELS_FROM_SUBSET_ONLY and request_data.get('model', 'mistral-nemo') not in AVAILABLE_MODELS:
        return ERROR_HANDLER(1002, request_data.get('model', 'mistral-nemo')) # Handle invalid model
    
    logger.debug(f"Proccessing {prompt_token} prompt tokens with model {request_data.get('model', 'mistral-nemo')}")

    if not image:
        payload = {
            "type": "CHAT_WITH_AI",
            "model": request_data.get('model', 'mistral-nemo'),
            "promptObject": {
                "prompt": all_messages,
                "isMixed": False,
                "webSearch": False
            }
        }
    else:
        payload = {
            "type": "CHAT_WITH_IMAGE",
            "model": request_data.get('model', 'mistral-nemo'),
            "promptObject": {
                "prompt": all_messages,
                "isMixed": False,
                "imageList": image_paths
            }
        }
    
    headers = {"API-KEY": api_key, 'Content-Type': 'application/json'}

    if not request_data.get('stream', False):
        # Non-Streaming Response
        logger.debug("Non-Streaming AI Response")
        response = requests.post(ONE_MIN_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        one_min_response = response.json()
        
        transformed_response = transform_response(one_min_response, request_data, prompt_token)
        response = make_response(jsonify(transformed_response))
        set_response_headers(response)
        
        return response, 200
    
    else:
        # Streaming Response
        logger.debug("Streaming AI Response")
        response_stream = requests.post(ONE_MIN_CONVERSATION_API_STREAMING_URL, data=json.dumps(payload), headers=headers, stream=True)
        if response_stream.status_code != 200:
            if response_stream.status_code == 401:
                return ERROR_HANDLER(1020)
            logger.error(f"An unknown error occurred while processing the user's request. Error code: {response_stream.status_code}")
            return ERROR_HANDLER(response_stream.status_code)
        return Response(stream_response(response_stream, request_data, request_data.get('model', 'mistral-nemo'), int(prompt_token)), content_type='text/event-stream')

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

def handle_options_request():
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    return response, 204

def transform_response(one_min_response, request_data, prompt_token):
    completion_token = calculate_token(one_min_response['aiRecord']["aiRecordDetail"]["resultObject"][0])
    logger.debug(f"Finished processing Non-Streaming response. Completion tokens: {str(completion_token)}")
    logger.debug(f"Total tokens: {str(completion_token + prompt_token)}")
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request_data.get('model', 'mistral-nemo'),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": one_min_response['aiRecord']["aiRecordDetail"]["resultObject"][0],
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_token,
            "completion_tokens": completion_token,
            "total_tokens": prompt_token + completion_token
        }
    }
    
def set_response_headers(response):
    response.headers['Content-Type'] = 'application/json'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['X-Request-ID'] = str (uuid.uuid4())

def stream_response(response, request_data, model, prompt_tokens):
    all_chunks = ""
    for chunk in response.iter_content(chunk_size=1024):
        finish_reason = None

        return_chunk = {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request_data.get('model', 'mistral-nemo'),
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": chunk.decode('utf-8')
                    },
                    "finish_reason": finish_reason
                }
            ]
        }
        all_chunks += chunk.decode('utf-8')
        yield f"data: {json.dumps(return_chunk)}\n\n"
        
    tokens = calculate_token(all_chunks)
    logger.debug(f"Finished processing streaming response. Completion tokens: {str(tokens)}")
    logger.debug(f"Total tokens: {str(tokens + prompt_tokens)}")
        
    # Final chunk when iteration stops
    final_chunk = {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": request_data.get('model', 'mistral-nemo'),
        "choices": [
            {
                "index": 0,
                "delta": {
                    "content": ""    
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": tokens,
            "total_tokens": tokens + prompt_tokens
        }
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"

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