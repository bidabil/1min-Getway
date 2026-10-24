"""Chat endpoints: OpenAI /v1/chat/completions, Anthropic /v1/messages, and /v1/models."""

import logging
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from ....bootstrap import Container
from ....domain.chat import ChatRequest, StreamStart, Usage
from ....domain.clients import ClientIdentity
from ....domain.errors import GatewayError, NotFoundError
from ....domain.models import ModelInfo
from ..dependencies import client_identity, get_container, json_body
from ..errors import is_anthropic_request
from ..streaming import open_stream, sse_response
from ..translators.anthropic_messages import (
    AnthropicStreamEncoder,
    count_tokens,
    parse_messages_request,
    render_message,
)
from ..translators.openai_chat import OpenAIStreamEncoder, parse_chat_request, render_completion

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/v1/chat/completions", tags=["OpenAI"])
async def chat_completions(
    request: Request,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> Response:
    chat_request, stream = parse_chat_request(await json_body(request))
    return await _run_chat(container, chat_request, stream, api="openai")


@router.post("/v1/messages", tags=["Anthropic"])
async def messages(
    request: Request,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> Response:
    chat_request, stream = parse_messages_request(await json_body(request))
    return await _run_chat(container, chat_request, stream, api="anthropic")


@router.post("/v1/messages/count_tokens", tags=["Anthropic"])
async def messages_count_tokens(
    request: Request,
    _client: ClientIdentity = Depends(client_identity),
) -> dict[str, int]:
    body = await json_body(request)
    body.setdefault("max_tokens", 1)
    chat_request, _ = parse_messages_request(body)
    return {"input_tokens": count_tokens(chat_request)}


@router.get("/v1/models", tags=["OpenAI", "Anthropic"])
async def list_models(
    request: Request,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    models = await container.models.list_models()
    if is_anthropic_request(request.url.path, request.headers):
        data = [_anthropic_model(model) for model in models]
        return {
            "data": data,
            "has_more": False,
            "first_id": data[0]["id"] if data else None,
            "last_id": data[-1]["id"] if data else None,
        }
    return {"object": "list", "data": [_openai_model(model) for model in models]}


@router.get("/v1/models/{model_id:path}", tags=["OpenAI", "Anthropic"])
async def get_model(
    model_id: str,
    request: Request,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    for model in await container.models.list_models():
        if model.id == model_id:
            if is_anthropic_request(request.url.path, request.headers):
                return _anthropic_model(model)
            return _openai_model(model)
    raise NotFoundError(
        f"The model '{model_id}' does not exist.", code="model_not_found", param="model"
    )


async def _run_chat(
    container: Container, chat_request: ChatRequest, stream: bool, *, api: str
) -> Response:
    started = time.perf_counter()
    anthropic = api == "anthropic"

    if not stream:
        try:
            result = await container.chat.complete(chat_request)
        except GatewayError:
            _record(container, chat_request.model, "unknown", api, "error", None, stream, started)
            raise
        backend = result.backend.value if result.backend else "unknown"
        _record(container, result.model, backend, api, "ok", result.usage, stream, started)
        body = (
            render_message(result, chat_request.model) if anthropic else render_completion(result)
        )
        return JSONResponse(body)

    events = container.chat.stream(chat_request)
    try:
        first = await open_stream(events)
    except GatewayError:
        _record(container, chat_request.model, "unknown", api, "error", None, stream, started)
        raise
    backend = first.backend.value if isinstance(first, StreamStart) and first.backend else "unknown"
    encoder: AnthropicStreamEncoder | OpenAIStreamEncoder = (
        AnthropicStreamEncoder(model=chat_request.model)
        if anthropic
        else OpenAIStreamEncoder(include_usage=chat_request.include_usage, model=chat_request.model)
    )

    def on_complete(outcome: str, usage: Usage | None) -> None:
        _record(container, chat_request.model, backend, api, outcome, usage, stream, started)

    return sse_response(first, events, encoder, on_complete)


def _record(
    container: Container,
    model: str,
    backend: str,
    api: str,
    outcome: str,
    usage: Usage | None,
    stream: bool,
    started: float,
) -> None:
    container.metrics.observe_chat(backend, api, outcome, usage)
    logger.info(
        "chat %s",
        outcome,
        extra={
            "model": model,
            "backend": backend,
            "stream": stream,
            "duration_ms": round((time.perf_counter() - started) * 1000),
        },
    )


def _openai_model(model: ModelInfo) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": model.id,
        "object": "model",
        "created": model.created,
        "owned_by": model.owned_by,
        "backend": model.backend.value,
    }
    for key, value in (
        ("alias_of", model.alias_of),
        ("name", model.name),
        ("vision", model.vision),
        ("max_output_tokens", model.max_output_tokens),
        ("deprecation_date", model.deprecation_date),
    ):
        if value is not None:
            body[key] = value
    return body


def _anthropic_model(model: ModelInfo) -> dict[str, Any]:
    created = datetime.fromtimestamp(model.created or 0, UTC).isoformat().replace("+00:00", "Z")
    return {
        "type": "model",
        "id": model.id,
        "display_name": model.name or model.id,
        "created_at": created,
    }
