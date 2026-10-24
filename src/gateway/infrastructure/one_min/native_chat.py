"""Adapter for the 1min.ai OpenAI-compatible API (/openai/v1).

Native function tools, JSON mode and streaming; text-only input.
"""

import json
import time
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

from ...domain.chat import (
    ChatRequest,
    ChatResult,
    ChatStreamEvent,
    FinishReason,
    Message,
    NamedToolChoice,
    RefusalDelta,
    StreamEnd,
    StreamStart,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    Usage,
)
from ...domain.errors import UpstreamError
from ...domain.models import Backend, ModelInfo
from .errors import error_from_payload
from .http import OneMinHttp, iter_lines
from .sse import iter_sse

CHAT_PATH = "/openai/v1/chat/completions"
MODELS_PATH = "/openai/v1/models"

_FINISH_REASONS: dict[str, FinishReason] = {
    "stop": "stop",
    "length": "length",
    "tool_calls": "tool_calls",
    "function_call": "tool_calls",
    "content_filter": "content_filter",
}


class NativeChatBackend:
    def __init__(self, http: OneMinHttp, *, timeout_s: float) -> None:
        self._http = http
        self._timeout = timeout_s

    async def complete(self, request: ChatRequest) -> ChatResult:
        data = await self._http.post_json(
            CHAT_PATH, build_payload(request, stream=False), auth="bearer", timeout_s=self._timeout
        )
        return parse_completion(data, request.model)

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        async with self._http.stream_post(
            CHAT_PATH, build_payload(request, stream=True), auth="bearer", timeout_s=self._timeout
        ) as response:
            started = False
            finish_reason: FinishReason = "stop"
            usage: Usage | None = None
            async for event in iter_sse(iter_lines(response)):
                if event.data == "[DONE]":
                    if not started:
                        yield _start(None, request.model)
                    yield StreamEnd(finish_reason, usage)
                    return
                try:
                    chunk = json.loads(event.data)
                except json.JSONDecodeError:
                    continue
                if (error := error_from_payload(chunk)) is not None:
                    raise error
                if not isinstance(chunk, dict):
                    continue
                if not started:
                    started = True
                    yield _start(chunk, request.model)
                if isinstance(chunk.get("usage"), dict):
                    usage = parse_usage(chunk["usage"])
                for choice in chunk.get("choices") or ():
                    if not isinstance(choice, dict):
                        continue
                    delta = choice.get("delta") or {}
                    if isinstance(delta.get("content"), str) and delta["content"]:
                        yield TextDelta(delta["content"])
                    if isinstance(delta.get("refusal"), str) and delta["refusal"]:
                        yield RefusalDelta(delta["refusal"])
                    for call in delta.get("tool_calls") or ():
                        if isinstance(call, dict):
                            yield _tool_call_delta(call)
                    if choice.get("finish_reason"):
                        finish_reason = _FINISH_REASONS.get(str(choice["finish_reason"]), "stop")
            raise UpstreamError(
                "The 1min.ai stream ended before completion.", code="incomplete_stream"
            )


class NativeModelList:
    def __init__(self, http: OneMinHttp, *, timeout_s: float = 15.0) -> None:
        self._http = http
        self._timeout = timeout_s

    async def list_models(self) -> Sequence[ModelInfo]:
        data = await self._http.get_json(MODELS_PATH, auth="bearer", timeout_s=self._timeout)
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise UpstreamError("1min.ai returned an unexpected model list.")
        models = []
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                models.append(
                    ModelInfo(
                        id=item["id"],
                        backend=Backend.NATIVE,
                        owned_by=str(item.get("owned_by") or "1min-ai"),
                        created=int(item.get("created") or 0),
                    )
                )
        return models


# --- Request building -------------------------------------------------------------------


def build_payload(request: ChatRequest, *, stream: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model,
        "messages": [_message(message) for message in request.messages],
    }
    options = request.options
    if options.max_output_tokens is not None:
        payload["max_completion_tokens"] = options.max_output_tokens
    for key, value in (
        ("temperature", options.temperature),
        ("top_p", options.top_p),
        ("presence_penalty", options.presence_penalty),
        ("frequency_penalty", options.frequency_penalty),
        ("reasoning_effort", options.reasoning_effort),
        ("parallel_tool_calls", options.parallel_tool_calls),
    ):
        if value is not None:
            payload[key] = value
    if options.stop:
        payload["stop"] = list(options.stop)
    if options.response_format is not None:
        response_format: dict[str, Any] = {"type": options.response_format.type}
        if options.response_format.json_schema is not None:
            response_format["json_schema"] = dict(options.response_format.json_schema)
        payload["response_format"] = response_format
    if request.tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    key: value
                    for key, value in (
                        ("name", tool.name),
                        ("description", tool.description),
                        (
                            "parameters",
                            dict(tool.parameters) or {"type": "object", "properties": {}},
                        ),
                        ("strict", tool.strict),
                    )
                    if value is not None
                },
            }
            for tool in request.tools
        ]
    if request.tool_choice is not None:
        if isinstance(request.tool_choice, NamedToolChoice):
            payload["tool_choice"] = {
                "type": "function",
                "function": {"name": request.tool_choice.name},
            }
        else:
            payload["tool_choice"] = request.tool_choice
    if stream:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    for key, value in request.extra.items():
        payload.setdefault(key, value)
    return payload


def _message(message: Message) -> dict[str, Any]:
    text = message.text()
    if message.role == "assistant":
        wire: dict[str, Any] = {"role": "assistant", "content": text or None}
        if message.tool_calls:
            wire["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in message.tool_calls
            ]
        elif wire["content"] is None:
            wire["content"] = ""
        return wire
    if message.role == "tool":
        content = text
        if message.is_error and not content.startswith("Error"):
            content = f"Error: {content}"
        return {"role": "tool", "tool_call_id": message.tool_call_id or "", "content": content}
    return {"role": message.role, "content": text}


# --- Response parsing -------------------------------------------------------------------


def parse_completion(data: Any, model: str) -> ChatResult:
    if not isinstance(data, dict):
        raise UpstreamError("1min.ai returned an unexpected completion.")
    if (error := error_from_payload(data)) is not None:
        raise error
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise UpstreamError("1min.ai returned a completion without choices.")
    choice = choices[0]
    message = choice.get("message") or {}
    tool_calls = tuple(
        ToolCall(
            id=str(call.get("id") or f"call_{uuid.uuid4().hex[:24]}"),
            name=str((call.get("function") or {}).get("name") or ""),
            arguments=str((call.get("function") or {}).get("arguments") or "{}"),
        )
        for call in message.get("tool_calls") or ()
        if isinstance(call, dict)
    )
    usage = data.get("usage")
    return ChatResult(
        id=str(data.get("id") or f"chatcmpl-{uuid.uuid4().hex}"),
        model=str(data.get("model") or model),
        created=int(data.get("created") or time.time()),
        text=message.get("content") if isinstance(message.get("content"), str) else None,
        tool_calls=tool_calls,
        finish_reason=_FINISH_REASONS.get(
            str(choice.get("finish_reason")), "tool_calls" if tool_calls else "stop"
        ),
        usage=parse_usage(usage) if isinstance(usage, dict) else None,
        refusal=message.get("refusal") if isinstance(message.get("refusal"), str) else None,
    )


def parse_usage(usage: dict[str, Any]) -> Usage:
    details = usage.get("completion_tokens_details")
    reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None
    return Usage(
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        reasoning_tokens=int(reasoning) if isinstance(reasoning, int) else None,
    )


def _start(chunk: dict[str, Any] | None, model: str) -> StreamStart:
    chunk = chunk or {}
    return StreamStart(
        id=str(chunk.get("id") or f"chatcmpl-{uuid.uuid4().hex}"),
        model=str(chunk.get("model") or model),
        created=int(chunk.get("created") or time.time()),
    )


def _tool_call_delta(call: dict[str, Any]) -> ToolCallDelta:
    function = call.get("function") or {}
    call_id, name, arguments = call.get("id"), function.get("name"), function.get("arguments")
    return ToolCallDelta(
        index=int(call.get("index") or 0),
        id=call_id if isinstance(call_id, str) else None,
        name=name if isinstance(name, str) else None,
        arguments=arguments if isinstance(arguments, str) else "",
    )
