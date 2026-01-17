import time
import uuid
import json
import logging
# Ensure this import matches your project structure
from ..infrastructure.token_service import calculate_token

# Updated logger for the completion transformation layer
logger = logging.getLogger("1min-gateway.completion-service")

def transform_response(one_min_response, model_name, prompt_token):
    """
    Transforms a non-streaming 1min.ai response into a standard OpenAI Chat Completion object.
    Includes safety checks using .get() to prevent server crashes on malformed data.
    """
    try:
        # Safe extraction of the text content from 1min.ai nested structure
        result_list = one_min_response.get('aiRecord', {}).get('aiRecordDetail', {}).get('resultObject', [])
        content = result_list[0] if result_list else "Error: No response content from provider."
        
        # Calculate tokens for the assistant's response
        completion_token = calculate_token(content)
        
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": prompt_token,
                "completion_tokens": completion_token,
                "total_tokens": prompt_token + completion_token
            }
        }
    except Exception as e:
        logger.error(f"Transformation Error (Non-stream): {str(e)}")
        # Returns a minimal error structure to avoid breaking the client UI
        return {"error": "Failed to transform 1min.ai response"}

def stream_response(response, model_name, prompt_tokens):
    """
    Handles Server-Sent Events (SSE) streaming.
    Re-packages chunks from 1min.ai into OpenAI-compatible stream chunks.
    """
    all_chunks = ""
    chat_id = f"chatcmpl-{uuid.uuid4()}" # Maintain the same ID throughout the stream
    
    # Iterate through the stream as chunks arrive
    for chunk in response.iter_content(chunk_size=None): 
        if not chunk:
            continue
            
        decoded_chunk = chunk.decode('utf-8', errors='ignore')
        all_chunks += decoded_chunk
        
        chunk_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": decoded_chunk},
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(chunk_data)}\n\n"
        
    # Final token calculation after the stream is fully collected
    completion_tokens = calculate_token(all_chunks)
    
    # Send the final metadata chunk containing usage statistics
    # Essential for modern clients that track token consumption
    final_chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_name,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"