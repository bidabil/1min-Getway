# openai_adapter.py
"""
Adaptateur pour transformer les réponses 1min.ai au format OpenAI
Aligné sur la documentation officielle : https://docs.1min.ai
"""

import json
import logging
import time
import uuid
from collections.abc import Generator
from typing import Any

from ..infrastructure.token_service import calculate_token

logger = logging.getLogger("1min-gateway.openai-adapter")


def transform_response(
    one_min_response: dict[str, Any],
    model_name: str,
    prompt_token: int,
) -> dict[str, Any]:
    """
    Transforme une réponse non-streaming 1min.ai en format OpenAI.

    Structure documentée de la réponse 1min.ai :
    {
        "aiRecord": {
            "aiRecordDetail": {
                "resultObject": ["contenu..."]
            }
        }
    }
    """
    try:
        # Extraction selon structure documentée
        ai_record = one_min_response.get("aiRecord", {})
        ai_record_detail = ai_record.get("aiRecordDetail", {})
        result_list = ai_record_detail.get("resultObject", [])

        # Le contenu est dans resultObject (array)
        if isinstance(result_list, list) and result_list:
            content = result_list[0]
        elif isinstance(result_list, str):
            content = result_list
        else:
            content = "Error: No response content."
            logger.warning(f"ADAPTER | resultObject vide ou invalide: {result_list}")

        completion_token = calculate_token(content, model_name)

        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_token,
                "completion_tokens": completion_token,
                "total_tokens": prompt_token + completion_token,
            },
        }
    except Exception as e:
        logger.error(f"ADAPTER | Erreur transformation: {str(e)}")
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": f"Error: {str(e)}"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_token,
                "completion_tokens": 0,
                "total_tokens": prompt_token,
            },
        }


def stream_response(
    response: Any,
    model_name: str,
    prompt_tokens: int,
) -> Generator[str, None, None]:
    """
    Gère le streaming SSE en transformant les chunks 1min.ai.

    Selon la doc : "For streaming features like chat, responses are
    streamed in real-time"
    """
    all_chunks_text = ""
    chat_id = f"chatcmpl-{uuid.uuid4()}"

    try:
        for line in response.iter_lines():
            if not line:
                continue

            decoded_line = line.decode("utf-8", errors="ignore").strip()

            # Nettoyage du préfixe "data: " si présent
            if decoded_line.startswith("data: "):
                decoded_line = decoded_line[6:]

            if decoded_line == "[DONE]":
                break

            if not decoded_line:
                continue

            content_to_send = ""

            # Tentative de parsing JSON
            try:
                data = json.loads(decoded_line)
                content_to_send = data.get("result", data.get("content", ""))
            except json.JSONDecodeError:
                # Texte brut (selon doc : streamed in real-time)
                content_to_send = decoded_line

            if not content_to_send:
                continue

            all_chunks_text += content_to_send

            # Format OpenAI
            chunk_data: dict[str, Any] = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {"index": 0, "delta": {"content": content_to_send}, "finish_reason": None}
                ],
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"

    except Exception as e:
        logger.error(f"ADAPTER | Erreur streaming: {str(e)}")

    # Metadata finale avec tokens
    completion_tokens = calculate_token(all_chunks_text, model_name)
    final_metadata: dict[str, Any] = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_name,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    yield f"data: {json.dumps(final_metadata)}\n\n"
    yield "data: [DONE]\n\n"
