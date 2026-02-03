# src/adapters/openai_adapter.py

import time
import uuid
import json
import logging
from ..infrastructure.token_service import calculate_token

# Logger pour la couche de transformation
logger = logging.getLogger("1min-gateway.openai-adapter")

def transform_response(one_min_response, model_name, prompt_token):
    """
    Transforme une réponse non-streaming 1min.ai en objet OpenAI Chat Completion.
    """
    try:
        # Extraction sécurisée selon la structure imbriquée de 1min.ai
        result_list = one_min_response.get('aiRecord', {}).get('aiRecordDetail', {}).get('resultObject', [])
        content = result_list[0] if result_list else "Error: No response content from provider."
        
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
        logger.error(f"ADAPTER | Erreur Transformation (Non-stream): {str(e)}")
        return {"error": "Failed to transform 1min.ai response"}

def stream_response(response, model_name, prompt_tokens):
    """
    Gère le streaming SSE en nettoyant les chunks de 1min.ai.
    Supporte les formats: Texte brut, JSON par chunk, et préfixes 'data:'.
    """
    all_chunks_text = ""
    chat_id = f"chatcmpl-{uuid.uuid4()}"
    
    # On itère sur les lignes du flux (plus sûr pour le SSE)
    for line in response.iter_lines():
        if not line:
            continue
            
        decoded_line = line.decode('utf-8', errors='ignore').strip()
        
        # 1. Nettoyage du préfixe "data: " si 1min.ai l'envoie déjà
        if decoded_line.startswith("data: "):
            decoded_line = decoded_line[6:]
        
        if decoded_line == "[DONE]":
            break

        content_to_send = ""
        
        # 2. Tentative de décodage JSON (si le chunk est un objet)
        try:
            data = json.loads(decoded_line)
            # Selon la doc 1min.ai, le texte peut être dans 'result' ou directement à la racine
            content_to_send = data.get("result", data.get("content", ""))
        except json.JSONDecodeError:
            # Si ce n't pas du JSON, c'est du texte brut
            content_to_send = decoded_line

        if not content_to_send:
            continue

        all_chunks_text += content_to_send
        
        # 3. Formatage pour OpenAI
        chunk_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": content_to_send},
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(chunk_data)}\n\n"
        
    # 4. Envoi des métadonnées finales (Tokens)
    completion_tokens = calculate_token(all_chunks_text)
    
    final_metadata = {
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
    
    yield f"data: {json.dumps(final_metadata)}\n\n"
    yield "data: [DONE]\n\n"