import time
import uuid
import json
import logging
from src.infrastructure.token_service import calculate_token

logger = logging.getLogger("1min-relay")

def transform_response(one_min_response, model_name, prompt_token):
    content = one_min_response['aiRecord']["aiRecordDetail"]["resultObject"][0]
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

def stream_response(response, model_name, prompt_tokens):
    all_chunks = ""
    for chunk in response.iter_content(chunk_size=1024):
        decoded_chunk = chunk.decode('utf-8')
        all_chunks += decoded_chunk
        
        chunk_data = {
            "id": f"chatcmpl-{uuid.uuid4()}",
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
        
    completion_tokens = calculate_token(all_chunks)
    final_chunk = {
        "id": f"chatcmpl-{uuid.uuid4()}",
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