# src/api/routes.py
"""
Routes FastAPI pour 1min-Gateway.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..application.use_cases import Failure, Success
from ..config import AVAILABLE_MODELS, ONE_MIN_FEATURE_API_URL, RATELIMIT_DEFAULT
from ..container import container
from ..domain.ports import ChatRequest
from ..infrastructure.circuit_breaker import api_circuit_breaker
from ..infrastructure.error_service import get_error_response
from ..infrastructure.health_service import (
    get_health_status_code,
    perform_health_check,
)
from ..infrastructure.logging_config import get_logger
from ..infrastructure.metrics import (
    get_metrics_output,
    update_circuit_breaker_metrics,
)
from ..infrastructure.model_cache import model_cache
from ..infrastructure.rate_limiter import api_key_rate_limiter
from ..infrastructure.token_service import calculate_token
from ..infrastructure.webhooks import WebhookEvent, webhook_manager
from .schemas import (
    ChatCompletionRequest,
    CircuitBreakerStats,
    HealthResponse,
    ModelsResponse,
)

# Use structured logger
logger = get_logger("1min-gateway.routes")

# Router FastAPI
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# DEPENDENCIES
# ============================================================================


def extract_api_key(
    api_key: str | None = Header(None, alias="API-KEY"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """Extrait la clé API des headers."""
    if api_key:
        return api_key
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    raise HTTPException(
        status_code=401,
        detail={
            "success": False,
            "error": {"code": "UNAUTHORIZED", "message": "API key is required"},
        },
    )


# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================


@router.get("/", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check avec statut du circuit breaker."""
    cb_stats = api_circuit_breaker.get_stats()
    return HealthResponse(
        status="ok",
        architecture="FastAPI + Clean Architecture",
        circuit_breaker={
            "state": cb_stats["state"],
            "failures": cb_stats["failure_count"],
        },
    )


@router.get("/health/detailed")
async def detailed_health(request: Request) -> JSONResponse:
    """
    Health check détaillé avec vérification des dépendances.

    Inclut:
    - Connectivité API 1min.ai
    - État du circuit breaker
    - Configuration
    - Memcached (optionnel)
    """
    # Perform comprehensive health check
    result = perform_health_check(
        include_api=True,
        include_memcached=True,
    )

    status_code = get_health_status_code(result)

    logger.info(
        "Health check performed",
        status=result.status.value,
        status_code=status_code,
    )

    return JSONResponse(
        content=result.to_dict(),
        status_code=status_code,
    )


@router.get("/health/circuit-breaker", response_model=CircuitBreakerStats)
async def circuit_breaker_status() -> CircuitBreakerStats:
    """Statistiques détaillées du circuit breaker."""
    stats = api_circuit_breaker.get_stats()
    return CircuitBreakerStats(**stats)


@router.post("/health/circuit-breaker/reset")
async def reset_circuit_breaker() -> dict[str, Any]:
    """Reset manuel du circuit breaker."""
    api_circuit_breaker.reset()
    return {"success": True, "message": "Circuit breaker reset successfully"}


# ============================================================================
# METRICS ENDPOINT (Prometheus)
# ============================================================================


@router.get("/metrics")
async def metrics_endpoint() -> str:
    """
    Endpoint Prometheus pour les métriques.

    Expose les métriques au format Prometheus text:
    - Requêtes HTTP (compteurs, histogrammes)
    - État du circuit breaker
    - Utilisation du cache
    - Requêtes par modèle
    """
    # Update circuit breaker metrics
    stats = api_circuit_breaker.get_stats()
    update_circuit_breaker_metrics(
        name="api",
        state=stats["state"],
        failures=stats["failure_count"],
    )

    return get_metrics_output()


# ============================================================================
# CACHE ENDPOINTS
# ============================================================================


@router.get("/cache/stats")
async def cache_stats() -> dict[str, Any]:
    """Statistiques du cache des modèles."""
    return model_cache.get_stats()


@router.post("/cache/invalidate")
async def invalidate_cache() -> dict[str, Any]:
    """Invalider tout le cache."""
    model_cache.clear()
    return {"success": True, "message": "Cache cleared successfully"}


# ============================================================================
# RATE LIMITING ENDPOINTS
# ============================================================================


@router.get("/rate-limit/stats")
async def rate_limit_stats() -> dict[str, Any]:
    """Statistiques du rate limiter."""
    return api_key_rate_limiter.get_stats()


@router.get("/rate-limit/usage/{api_key}")
async def rate_limit_usage(api_key: str) -> dict[str, Any]:
    """Utilisation actuelle pour une clé API."""
    usage = api_key_rate_limiter.get_usage(api_key)
    if usage is None:
        return {"api_key": api_key, "usage": None, "message": "No usage recorded"}
    return {"api_key": api_key, "usage": usage}


@router.post("/rate-limit/reset/{api_key}")
async def rate_limit_reset(api_key: str) -> dict[str, Any]:
    """Réinitialiser le compteur pour une clé API."""
    reset = api_key_rate_limiter.reset_usage(api_key)
    return {"success": reset, "message": "Usage reset" if reset else "No usage found"}


# ============================================================================
# WEBHOOKS ENDPOINTS
# ============================================================================


@router.get("/webhooks")
async def list_webhooks() -> list[dict[str, Any]]:
    """Liste tous les webhooks enregistrés."""
    return webhook_manager.list_webhooks()


@router.get("/webhooks/stats")
async def webhook_stats() -> dict[str, Any]:
    """Statistiques des webhooks."""
    return webhook_manager.get_stats()


@router.get("/webhooks/history")
async def webhook_history(limit: int = 20) -> list[dict[str, Any]]:
    """Historique des livraisons de webhooks."""
    return webhook_manager.get_history(limit)


@router.post("/webhooks/register")
async def register_webhook(
    name: str,
    url: str,
    secret: str,
    events: list[str] | None = None,
) -> dict[str, Any]:
    """
    Enregistrer un nouveau webhook.

    Args:
        name: Nom unique du webhook
        url: URL du endpoint
        secret: Secret pour la signature
        events: Liste des événements (optionnel, tous par défaut)
    """

    event_list = None
    if events:
        event_list = [WebhookEvent(e) for e in events]

    webhook_manager.register(name, url, secret, event_list)
    return {"success": True, "message": f"Webhook '{name}' registered"}


@router.delete("/webhooks/{name}")
async def unregister_webhook(name: str) -> dict[str, Any]:
    """Supprimer un webhook."""
    removed = webhook_manager.unregister(name)
    return {"success": removed, "message": "Webhook removed" if removed else "Webhook not found"}


# ============================================================================
# MODELS ENDPOINT
# ============================================================================


@router.get("/v1/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """
    Liste les modèles disponibles (format OpenAI).

    Retourne la liste des modèles supportés par la gateway.
    Les modèles sont mis en cache pour améliorer les performances.
    """
    from .schemas import ModelInfo

    def fetch_models() -> list[ModelInfo]:
        return [
            ModelInfo(id=model, created=1700000000, owned_by="1min-ai")
            for model in AVAILABLE_MODELS
        ]

    models = model_cache.get_or_fetch("available_models", fetch_models)
    return ModelsResponse(data=models)


# ============================================================================
# CHAT COMPLETIONS ENDPOINT
# ============================================================================


@router.post("/v1/chat/completions", response_model=None)
@limiter.limit(RATELIMIT_DEFAULT)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    api_key: str = Depends(extract_api_key),
):
    """
    Endpoint principal de chat completion.

    Compatible avec le format OpenAI API.
    Supporte le streaming et le mode non-streaming.
    """
    # --- 1. VALIDATION API KEY ---
    auth_result = container.validate_api_key.execute(api_key)
    if isinstance(auth_result, Failure):
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {"code": auth_result.error_code, "message": auth_result.message},
            },
        )

    # --- 2. PRÉPARATION DE LA REQUÊTE ---
    # Conversion des messages en format dict
    messages = [
        {"role": msg.role, "content": msg.content if isinstance(msg.content, str) else msg.content}
        for msg in body.messages
    ]

    # Extra params pour 1min.ai
    extra_params = {}
    if body.web_search:
        extra_params["web_search"] = body.web_search
    if body.file_ids:
        extra_params["file_ids"] = body.file_ids
    if body.temperature is not None:
        extra_params["temperature"] = body.temperature
    if body.max_tokens is not None:
        extra_params["max_tokens"] = body.max_tokens

    chat_request = ChatRequest(
        api_key=api_key,
        model=body.model,
        messages=messages,
        stream=body.stream,
        extra_params=extra_params,
    )

    # --- 3. EXÉCUTION DU USE CASE ---
    result = container.chat_completion.execute(chat_request)

    if isinstance(result, Failure):
        error_payload, status = get_error_response_from_failure(result)
        raise HTTPException(status_code=status, detail={"success": False, "error": error_payload})

    context = result.data

    # --- 4. CALCUL DES TOKENS ---
    prompt_text: str = context.prompt_object.get("prompt", "")
    tokens_result = container.calculate_tokens.execute(prompt_text, chat_request.model)
    prompt_token_count: int = tokens_result.data if isinstance(tokens_result, Success) else 0

    # --- 5. VÉRIFICATION CIRCUIT BREAKER ---
    if not api_circuit_breaker.can_execute():
        logger.warning("CIRCUIT_BREAKER | Requête bloquée - API 1min.ai indisponible")
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Service temporarily unavailable. Please retry later.",
                },
            },
        )

    # --- 6. APPEL API UPSTREAM ---
    payload: dict[str, Any] = {
        "type": context.type,
        "model": chat_request.model,
        "promptObject": context.prompt_object,
    }
    if context.session_id:
        payload["conversationId"] = context.session_id

    headers: dict[str, str] = {"API-KEY": api_key, "Content-Type": "application/json"}

    if not body.stream:
        # Mode non-streaming
        return await _handle_non_streaming(payload, headers, body.model, prompt_token_count)
    else:
        # Mode streaming
        return await _handle_streaming(payload, headers, body.model, prompt_token_count)


async def _handle_non_streaming(
    payload: dict[str, Any],
    headers: dict[str, str],
    model: str,
    prompt_tokens: int,
) -> JSONResponse:
    """Gère une requête non-streaming."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                ONE_MIN_FEATURE_API_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            api_circuit_breaker.record_success()

            # Transformation de la réponse
            data = response.json()
            transformed = _transform_response(data, model, prompt_tokens)

            return JSONResponse(content=transformed, status_code=200)

    except httpx.HTTPStatusError as e:
        api_circuit_breaker.record_failure()
        status_code = e.response.status_code if e.response else 500
        error_payload, status = get_error_response(status_code)
        raise HTTPException(
            status_code=status, detail={"success": False, "error": error_payload}
        ) from None
    except httpx.TimeoutException as e:
        api_circuit_breaker.record_failure()
        logger.error(f"TIMEOUT | Appel API 1min.ai: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail={
                "success": False,
                "error": {"code": "TIMEOUT", "message": "API request timed out"},
            },
        ) from None
    except httpx.ConnectError as e:
        api_circuit_breaker.record_failure()
        logger.error(f"CONNECTION_ERROR | API 1min.ai: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {"code": "SERVICE_UNAVAILABLE", "message": "Unable to connect to API"},
            },
        ) from None
    except Exception as e:
        api_circuit_breaker.record_failure()
        logger.error(f"UNEXPECTED_ERROR | {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
            },
        ) from None


async def _handle_streaming(
    payload: dict[str, Any],
    headers: dict[str, str],
    model: str,
    prompt_tokens: int,
) -> StreamingResponse:
    """Gère une requête streaming avec SSE."""

    streaming_url = f"{ONE_MIN_FEATURE_API_URL}?isStreaming=true"

    async def stream_generator() -> AsyncGenerator[str, None]:
        """Générateur asynchrone pour le streaming SSE."""
        import time
        import uuid

        chat_id = f"chatcmpl-{uuid.uuid4()}"
        all_chunks_text = ""

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    streaming_url,
                    json=payload,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    api_circuit_breaker.record_success()

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        decoded_line = line.strip()

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
                            content_to_send = decoded_line

                        if not content_to_send:
                            continue

                        all_chunks_text += content_to_send

                        # Format OpenAI
                        chunk_data = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": content_to_send},
                                    "finish_reason": None,
                                }
                            ],
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

        except Exception as e:
            api_circuit_breaker.record_failure()
            logger.error(f"STREAMING_ERROR | {str(e)}")
            error_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": f"\n\n[Error: {str(e)}]"},
                        "finish_reason": "error",
                    }
                ],
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            return

        # Metadata finale avec tokens
        completion_tokens = calculate_token(all_chunks_text, model)
        final_metadata = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
        yield f"data: {json.dumps(final_metadata)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _transform_response(
    one_min_response: dict[str, Any],
    model_name: str,
    prompt_token: int,
) -> dict[str, Any]:
    """Transforme une réponse 1min.ai en format OpenAI."""
    import time
    import uuid

    try:
        ai_record = one_min_response.get("aiRecord", {})
        ai_record_detail = ai_record.get("aiRecordDetail", {})
        result_list = ai_record_detail.get("resultObject", [])

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


def get_error_response_from_failure(failure: Failure) -> tuple[dict[str, str], int]:
    """Convertit un Failure en réponse d'erreur HTTP."""
    error_map: dict[str, tuple[dict[str, str], int]] = {
        "MODEL_NOT_FOUND": ({"code": failure.error_code, "message": failure.message}, 404),
        "INVALID_REQUEST": ({"code": failure.error_code, "message": failure.message}, 400),
        "UNAUTHORIZED": ({"code": failure.error_code, "message": failure.message}, 401),
        "CONTEXT_ERROR": ({"code": failure.error_code, "message": failure.message}, 500),
        "INTERNAL_ERROR": ({"code": failure.error_code, "message": failure.message}, 500),
    }
    return error_map.get(failure.error_code, ({"code": "UNKNOWN", "message": failure.message}, 500))
