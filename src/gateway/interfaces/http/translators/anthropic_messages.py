"""Anthropic Messages wire format <-> domain."""

import json
import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ....domain.chat import (
    ChatRequest,
    ChatResult,
    ChatStreamEvent,
    ContentPart,
    FilePart,
    GenerationOptions,
    ImagePart,
    Message,
    NamedToolChoice,
    RefusalDelta,
    StreamEnd,
    StreamStart,
    TextDelta,
    TextPart,
    ToolCall,
    ToolCallDelta,
    ToolChoice,
    ToolDefinition,
    Usage,
    WebSearch,
)
from ....domain.errors import GatewayError
from ....domain.services.tokens import estimate_tokens
from ..errors import error_body
from .common import (
    as_bool,
    as_float,
    as_int,
    as_mapping,
    as_stop,
    as_str,
    invalid,
    json_object,
    sse_frame,
)

logger = logging.getLogger(__name__)

_STOP_REASONS = {"tool_calls": "tool_use", "length": "max_tokens", "content_filter": "refusal"}
_IGNORED_BLOCKS = frozenset(
    {
        "thinking",
        "redacted_thinking",
        "server_tool_use",
        "web_search_tool_result",
        "container_upload",
    }
)


def parse_messages_request(body: Mapping[str, Any]) -> tuple[ChatRequest, bool]:
    model = as_str(body.get("model"), "model", required=True) or ""
    max_tokens = as_int(body.get("max_tokens"), "max_tokens", minimum=1)
    if max_tokens is None:
        invalid("'max_tokens' is required.", "max_tokens")

    messages: list[Message] = []
    system = body.get("system")
    if system is not None:
        text = _system_text(system)
        if text:
            messages.append(Message(role="system", content=(TextPart(text),)))

    raw_messages = body.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        invalid("'messages' must be a non-empty array.", "messages")
    for index, raw in enumerate(raw_messages):
        messages.extend(_message(raw, index))

    tools, web_search = _tools(body.get("tools"))
    tool_choice, parallel = _tool_choice(body.get("tool_choice"))
    metadata = as_mapping(body.get("metadata"), "metadata") or {}
    options = GenerationOptions(
        max_output_tokens=max_tokens,
        temperature=as_float(body.get("temperature"), "temperature"),
        top_p=as_float(body.get("top_p"), "top_p"),
        stop=as_stop(body.get("stop_sequences"), "stop_sequences"),
        parallel_tool_calls=parallel,
        user=metadata.get("user_id") if isinstance(metadata.get("user_id"), str) else None,
    )
    request = ChatRequest(
        model=model,
        messages=tuple(messages),
        tools=tools,
        tool_choice=tool_choice if tools else None,
        options=options,
        web_search=web_search,
        include_usage=True,
    )
    return request, bool(as_bool(body.get("stream"), "stream"))


def _system_text(system: Any) -> str:
    if isinstance(system, str):
        return system
    if isinstance(system, list):
        return "\n\n".join(
            block["text"]
            for block in system
            if isinstance(block, Mapping) and isinstance(block.get("text"), str)
        )
    invalid("'system' must be a string or an array of text blocks.", "system")


def _message(raw: Any, index: int) -> list[Message]:
    param = f"messages[{index}]"
    if not isinstance(raw, Mapping) or raw.get("role") not in ("user", "assistant"):
        invalid(f"'{param}.role' must be 'user' or 'assistant'.", f"{param}.role")
    role = raw["role"]
    content = raw.get("content")
    if isinstance(content, str):
        return [Message(role=role, content=(TextPart(content),) if content else ())]
    if not isinstance(content, list):
        invalid(f"'{param}.content' must be a string or an array of blocks.", f"{param}.content")

    parts: list[ContentPart] = []
    tool_calls: list[ToolCall] = []
    tool_results: list[Message] = []
    for block_index, block in enumerate(content):
        block_param = f"{param}.content[{block_index}]"
        if not isinstance(block, Mapping):
            invalid(f"'{block_param}' must be an object.", block_param)
        kind = block.get("type")
        if kind == "text":
            parts.append(
                TextPart(as_str(block.get("text"), f"{block_param}.text", required=True) or "")
            )
        elif kind == "image":
            parts.append(_image(block.get("source"), block_param))
        elif kind == "document":
            parts.append(_document(block, block_param))
        elif kind == "tool_use" and role == "assistant":
            tool_calls.append(
                ToolCall(
                    id=as_str(block.get("id"), f"{block_param}.id", required=True) or "",
                    name=as_str(block.get("name"), f"{block_param}.name", required=True) or "",
                    arguments=json.dumps(block.get("input") or {}, ensure_ascii=False),
                )
            )
        elif kind == "tool_result" and role == "user":
            tool_results.append(_tool_result(block, block_param))
        elif kind in _IGNORED_BLOCKS:
            continue
        else:
            invalid(f"Content block type '{kind}' is not supported here.", f"{block_param}.type")

    if role == "assistant":
        return [Message(role="assistant", content=tuple(parts), tool_calls=tuple(tool_calls))]
    # OpenAI-style ordering: tool results come right after the assistant tool calls.
    messages = list(tool_results)
    if parts:
        messages.append(Message(role="user", content=tuple(parts)))
    return messages


def _image(source: Any, param: str) -> ImagePart:
    source = as_mapping(source, f"{param}.source") or {}
    if source.get("type") == "base64":
        media_type = as_str(source.get("media_type"), f"{param}.source.media_type", required=True)
        data = as_str(source.get("data"), f"{param}.source.data", required=True)
        return ImagePart(f"data:{media_type};base64,{data}")
    if source.get("type") == "url":
        return ImagePart(as_str(source.get("url"), f"{param}.source.url", required=True) or "")
    invalid("Image sources must be of type 'base64' or 'url'.", f"{param}.source.type")


def _document(block: Mapping[str, Any], param: str) -> ContentPart:
    source = as_mapping(block.get("source"), f"{param}.source") or {}
    title = block.get("title") if isinstance(block.get("title"), str) else None
    if source.get("type") == "base64":
        media_type = as_str(source.get("media_type"), f"{param}.source.media_type", required=True)
        data = as_str(source.get("data"), f"{param}.source.data", required=True)
        return FilePart(data=f"data:{media_type};base64,{data}", filename=title)
    if source.get("type") == "text":
        text = as_str(source.get("data"), f"{param}.source.data", required=True) or ""
        return TextPart(f"[document {title}]\n{text}" if title else text)
    invalid("Document sources must be of type 'base64' or 'text'.", f"{param}.source.type")


def _tool_result(block: Mapping[str, Any], param: str) -> Message:
    tool_use_id = as_str(block.get("tool_use_id"), f"{param}.tool_use_id", required=True)
    content = block.get("content")
    parts: list[ContentPart] = []
    if isinstance(content, str):
        parts.append(TextPart(content))
    elif isinstance(content, list):
        for item in content:
            if (
                isinstance(item, Mapping)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            ):
                parts.append(TextPart(item["text"]))
            elif isinstance(item, Mapping) and item.get("type") == "image":
                parts.append(_image(item.get("source"), param))
    return Message(
        role="tool",
        content=tuple(parts),
        tool_call_id=tool_use_id,
        is_error=bool(block.get("is_error")),
    )


def _tools(raw: Any) -> tuple[tuple[ToolDefinition, ...], WebSearch | None]:
    if raw is None:
        return (), None
    if not isinstance(raw, list):
        invalid("'tools' must be an array.", "tools")
    tools: list[ToolDefinition] = []
    web_search: WebSearch | None = None
    for index, tool in enumerate(raw):
        param = f"tools[{index}]"
        if not isinstance(tool, Mapping):
            invalid(f"'{param}' must be an object.", param)
        kind = tool.get("type")
        if isinstance(kind, str) and kind.startswith("web_search"):
            web_search = WebSearch()  # Anthropic's server-side search maps to 1min.ai web search
            continue
        if kind not in (None, "custom"):
            invalid(f"Tool type '{kind}' is not supported.", f"{param}.type")
        tools.append(
            ToolDefinition(
                name=as_str(tool.get("name"), f"{param}.name", required=True) or "",
                description=as_str(tool.get("description"), f"{param}.description"),
                parameters=dict(
                    as_mapping(tool.get("input_schema"), f"{param}.input_schema") or {}
                ),
            )
        )
    return tuple(tools), web_search


def _tool_choice(raw: Any) -> tuple[ToolChoice | None, bool | None]:
    if raw is None:
        return None, None
    choice = as_mapping(raw, "tool_choice") or {}
    parallel = False if choice.get("disable_parallel_tool_use") is True else None
    kind = choice.get("type")
    if kind == "auto":
        return "auto", parallel
    if kind == "any":
        return "required", parallel
    if kind == "none":
        return "none", parallel
    if kind == "tool" and isinstance(choice.get("name"), str):
        return NamedToolChoice(choice["name"]), parallel
    invalid("'tool_choice.type' must be auto, any, tool or none.", "tool_choice")


# --- Responses ----------------------------------------------------------------------------


def message_id(completion_id: str) -> str:
    suffix = completion_id.removeprefix("chatcmpl-")
    return suffix if suffix.startswith("msg_") else f"msg_{suffix}"


def stop_reason(finish_reason: str) -> str:
    return _STOP_REASONS.get(finish_reason, "end_turn")


def render_message(result: ChatResult, model: str) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    if result.text:
        content.append({"type": "text", "text": result.text})
    elif result.refusal:
        content.append({"type": "text", "text": result.refusal})
    for call in result.tool_calls:
        content.append(
            {
                "type": "tool_use",
                "id": call.id,
                "name": call.name,
                "input": json_object(call.arguments),
            }
        )
    usage = result.usage or Usage(0, 0)
    return {
        "id": message_id(result.id),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": "refusal"
        if result.refusal and not result.text
        else stop_reason(result.finish_reason),
        "stop_sequence": None,
        "usage": {"input_tokens": usage.prompt_tokens, "output_tokens": usage.completion_tokens},
    }


def count_tokens(request: ChatRequest) -> int:
    text = "\n".join(message.text() for message in request.messages)
    for message in request.messages:
        text += "".join(call.arguments for call in message.tool_calls)
    for tool in request.tools:
        text += tool.name + (tool.description or "") + json.dumps(dict(tool.parameters))
    images = sum(len(message.images()) for message in request.messages)
    return estimate_tokens(text) + 1000 * images


@dataclass
class _PendingTool:
    id: str
    name: str
    arguments: str = ""


class AnthropicStreamEncoder:
    """Turns domain stream events into Anthropic Messages SSE events.

    Text streams live. Tool calls are emitted as complete tool_use blocks at the end, which
    keeps content blocks strictly sequential even when upstream fragments interleave.
    """

    def __init__(self, *, model: str) -> None:
        self._model = model
        self._block_index = -1
        self._text_open = False
        self._tools: dict[int, _PendingTool] = {}

    def encode(self, event: ChatStreamEvent) -> list[str]:
        if isinstance(event, StreamStart):
            message: dict[str, Any] = {
                "id": message_id(event.id),
                "type": "message",
                "role": "assistant",
                "model": self._model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }
            return [sse_frame({"type": "message_start", "message": message}, "message_start")]
        if isinstance(event, TextDelta | RefusalDelta):
            frames: list[str] = []
            if not self._text_open:
                self._block_index += 1
                self._text_open = True
                frames.append(
                    sse_frame(
                        {
                            "type": "content_block_start",
                            "index": self._block_index,
                            "content_block": {"type": "text", "text": ""},
                        },
                        "content_block_start",
                    )
                )
            frames.append(
                sse_frame(
                    {
                        "type": "content_block_delta",
                        "index": self._block_index,
                        "delta": {"type": "text_delta", "text": event.text},
                    },
                    "content_block_delta",
                )
            )
            return frames
        if isinstance(event, ToolCallDelta):
            pending = self._tools.get(event.index)
            if pending is None:
                pending = _PendingTool(
                    id=event.id or f"toolu_{uuid.uuid4().hex[:24]}", name=event.name or ""
                )
                self._tools[event.index] = pending
            if event.name and not pending.name:
                pending.name = event.name
            pending.arguments += event.arguments
            return []
        return self._finish(event)

    def _finish(self, event: StreamEnd) -> list[str]:
        frames: list[str] = []
        if self._text_open:
            frames.append(self._block_stop())
            self._text_open = False
        for _, tool in sorted(self._tools.items()):
            self._block_index += 1
            frames.append(
                sse_frame(
                    {
                        "type": "content_block_start",
                        "index": self._block_index,
                        "content_block": {
                            "type": "tool_use",
                            "id": tool.id,
                            "name": tool.name,
                            "input": {},
                        },
                    },
                    "content_block_start",
                )
            )
            frames.append(
                sse_frame(
                    {
                        "type": "content_block_delta",
                        "index": self._block_index,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": tool.arguments or "{}",
                        },
                    },
                    "content_block_delta",
                )
            )
            frames.append(self._block_stop())
        usage = event.usage or Usage(0, 0)
        frames.append(
            sse_frame(
                {
                    "type": "message_delta",
                    "delta": {
                        "stop_reason": stop_reason(event.finish_reason),
                        "stop_sequence": None,
                    },
                    "usage": {
                        "input_tokens": usage.prompt_tokens,
                        "output_tokens": usage.completion_tokens,
                    },
                },
                "message_delta",
            )
        )
        frames.append(sse_frame({"type": "message_stop"}, "message_stop"))
        return frames

    def _block_stop(self) -> str:
        return sse_frame(
            {"type": "content_block_stop", "index": self._block_index}, "content_block_stop"
        )

    def error(self, error: GatewayError) -> str:
        return sse_frame(error_body(error, anthropic=True), "error")
