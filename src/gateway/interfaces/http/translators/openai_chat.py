"""OpenAI Chat Completions wire format <-> domain."""

import uuid
from collections.abc import Mapping
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
    ResponseFormat,
    Role,
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
from ..errors import error_body
from .common import (
    as_bool,
    as_float,
    as_int,
    as_mapping,
    as_stop,
    as_str,
    invalid,
    json_arguments,
    sse_frame,
)

_ROLES: tuple[Role, ...] = ("system", "developer", "user", "assistant", "tool")


def parse_chat_request(body: Mapping[str, Any]) -> tuple[ChatRequest, bool]:
    model = as_str(body.get("model"), "model", required=True) or ""
    raw_messages = body.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        invalid("'messages' must be a non-empty array.", "messages")
    messages = tuple(_message(raw, index) for index, raw in enumerate(raw_messages))

    n = as_int(body.get("n"), "n")
    if n not in (None, 1):
        invalid("Only n=1 is supported.", "n")

    tools = _tools(body)
    stream = bool(as_bool(body.get("stream"), "stream"))
    stream_options = as_mapping(body.get("stream_options"), "stream_options") or {}

    max_tokens = as_int(body.get("max_completion_tokens"), "max_completion_tokens", minimum=1)
    if max_tokens is None:
        max_tokens = as_int(body.get("max_tokens"), "max_tokens", minimum=1)

    options = GenerationOptions(
        max_output_tokens=max_tokens,
        temperature=as_float(body.get("temperature"), "temperature"),
        top_p=as_float(body.get("top_p"), "top_p"),
        stop=as_stop(body.get("stop"), "stop"),
        presence_penalty=as_float(body.get("presence_penalty"), "presence_penalty"),
        frequency_penalty=as_float(body.get("frequency_penalty"), "frequency_penalty"),
        seed=as_int(body.get("seed"), "seed"),
        reasoning_effort=as_str(body.get("reasoning_effort"), "reasoning_effort"),
        response_format=_response_format(body.get("response_format")),
        parallel_tool_calls=as_bool(body.get("parallel_tool_calls"), "parallel_tool_calls"),
        user=as_str(body.get("user"), "user"),
    )
    request = ChatRequest(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=_tool_choice(body),
        options=options,
        web_search=_web_search(body),
        file_ids=_file_ids(body.get("file_ids")),
        include_usage=bool(stream_options.get("include_usage")),
        extra=dict(as_mapping(body.get("upstream_extra"), "upstream_extra") or {}),
    )
    return request, stream


def _message(raw: Any, index: int) -> Message:
    param = f"messages[{index}]"
    if not isinstance(raw, Mapping):
        invalid(f"'{param}' must be an object.", param)
    role = raw.get("role")
    if role == "function":
        role = "tool"
    if role not in _ROLES:
        invalid(f"'{param}.role' must be one of {', '.join(_ROLES)}.", f"{param}.role")

    tool_calls: list[ToolCall] = []
    for call_index, call in enumerate(raw.get("tool_calls") or ()):
        call_param = f"{param}.tool_calls[{call_index}]"
        if not isinstance(call, Mapping) or not isinstance(call.get("function"), Mapping):
            invalid(f"'{call_param}' must be a function tool call.", call_param)
        function = call["function"]
        tool_calls.append(
            ToolCall(
                id=as_str(call.get("id"), f"{call_param}.id") or f"call_{uuid.uuid4().hex[:24]}",
                name=as_str(function.get("name"), f"{call_param}.function.name", required=True)
                or "",
                arguments=json_arguments(function.get("arguments")),
            )
        )
    legacy_call = raw.get("function_call")
    if isinstance(legacy_call, Mapping) and not tool_calls:
        tool_calls.append(
            ToolCall(
                id=f"call_{uuid.uuid4().hex[:24]}",
                name=str(legacy_call.get("name") or ""),
                arguments=json_arguments(legacy_call.get("arguments")),
            )
        )

    return Message(
        role=role,
        content=_content(raw.get("content"), f"{param}.content"),
        tool_calls=tuple(tool_calls),
        tool_call_id=as_str(raw.get("tool_call_id"), f"{param}.tool_call_id"),
        name=as_str(raw.get("name"), f"{param}.name"),
    )


def _content(raw: Any, param: str) -> tuple[ContentPart, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (TextPart(raw),) if raw else ()
    if not isinstance(raw, list):
        invalid(f"'{param}' must be a string or an array of content parts.", param)
    parts: list[ContentPart] = []
    for index, item in enumerate(raw):
        item_param = f"{param}[{index}]"
        if not isinstance(item, Mapping):
            invalid(f"'{item_param}' must be an object.", item_param)
        kind = item.get("type")
        if kind in ("text", "input_text", "output_text"):
            parts.append(
                TextPart(as_str(item.get("text"), f"{item_param}.text", required=True) or "")
            )
        elif kind == "refusal":
            parts.append(TextPart(as_str(item.get("refusal"), f"{item_param}.refusal") or ""))
        elif kind == "image_url":
            image = item.get("image_url")
            if isinstance(image, str):
                parts.append(ImagePart(image))
            elif isinstance(image, Mapping) and isinstance(image.get("url"), str):
                parts.append(
                    ImagePart(
                        image["url"], as_str(image.get("detail"), f"{item_param}.image_url.detail")
                    )
                )
            else:
                invalid(f"'{item_param}.image_url.url' is required.", f"{item_param}.image_url")
        elif kind == "file":
            file = as_mapping(item.get("file"), f"{item_param}.file") or {}
            if not file.get("file_data") and not file.get("file_id"):
                invalid(
                    f"'{item_param}.file' needs 'file_data' or 'file_id'.", f"{item_param}.file"
                )
            parts.append(
                FilePart(
                    data=as_str(file.get("file_data"), f"{item_param}.file.file_data"),
                    file_id=as_str(file.get("file_id"), f"{item_param}.file.file_id"),
                    filename=as_str(file.get("filename"), f"{item_param}.file.filename"),
                )
            )
        else:
            invalid(f"Content part type '{kind}' is not supported.", f"{item_param}.type")
    return tuple(parts)


def _tools(body: Mapping[str, Any]) -> tuple[ToolDefinition, ...]:
    raw_tools = body.get("tools")
    if raw_tools is None and isinstance(body.get("functions"), list):
        raw_tools = [{"type": "function", "function": function} for function in body["functions"]]
    if raw_tools is None:
        return ()
    if not isinstance(raw_tools, list):
        invalid("'tools' must be an array.", "tools")
    tools: list[ToolDefinition] = []
    for index, tool in enumerate(raw_tools):
        param = f"tools[{index}]"
        if not isinstance(tool, Mapping) or tool.get("type", "function") != "function":
            invalid(f"'{param}': only function tools are supported.", param)
        function = as_mapping(tool.get("function"), f"{param}.function") or {}
        tools.append(
            ToolDefinition(
                name=as_str(function.get("name"), f"{param}.function.name", required=True) or "",
                description=as_str(function.get("description"), f"{param}.function.description"),
                parameters=dict(
                    as_mapping(function.get("parameters"), f"{param}.function.parameters") or {}
                ),
                strict=as_bool(function.get("strict"), f"{param}.function.strict"),
            )
        )
    return tuple(tools)


def _tool_choice(body: Mapping[str, Any]) -> ToolChoice | None:
    raw = body.get("tool_choice", body.get("function_call"))
    if raw is None:
        return None
    if raw in ("auto", "none", "required"):
        return raw  # type: ignore[no-any-return]
    if isinstance(raw, Mapping):
        function = raw.get("function") if isinstance(raw.get("function"), Mapping) else raw
        name = function.get("name") if isinstance(function, Mapping) else None
        if isinstance(name, str) and name:
            return NamedToolChoice(name)
    invalid("'tool_choice' must be 'auto', 'none', 'required' or a named function.", "tool_choice")


def _response_format(raw: Any) -> ResponseFormat | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping) or raw.get("type") not in (
        "text",
        "json_object",
        "json_schema",
    ):
        invalid(
            "'response_format.type' must be text, json_object or json_schema.", "response_format"
        )
    schema = raw.get("json_schema")
    return ResponseFormat(
        type=raw["type"], json_schema=dict(schema) if isinstance(schema, Mapping) else None
    )


def _web_search(body: Mapping[str, Any]) -> WebSearch | None:
    raw = body.get("web_search")
    if raw is None and body.get("web_search_options") is not None:
        raw = True
    if raw is None or raw is False:
        return None
    if raw is True:
        return WebSearch()
    options = as_mapping(raw, "web_search") or {}
    return WebSearch(
        enabled=bool(options.get("enabled", True)),
        sites=as_int(options.get("sites"), "web_search.sites", minimum=1),
        max_words=as_int(options.get("max_words"), "web_search.max_words", minimum=1),
    )


def _file_ids(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        invalid("'file_ids' must be an array of strings.", "file_ids")
    return tuple(raw)


# --- Responses ----------------------------------------------------------------------------


def usage_body(usage: Usage) -> dict[str, Any]:
    body: dict[str, Any] = {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }
    if usage.reasoning_tokens is not None:
        body["completion_tokens_details"] = {"reasoning_tokens": usage.reasoning_tokens}
    return body


def render_completion(result: ChatResult) -> dict[str, Any]:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": result.text,
        "refusal": result.refusal,
    }
    if result.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in result.tool_calls
        ]
    body: dict[str, Any] = {
        "id": result.id,
        "object": "chat.completion",
        "created": result.created,
        "model": result.model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": result.finish_reason,
                "logprobs": None,
            }
        ],
    }
    if result.usage is not None:
        body["usage"] = usage_body(result.usage)
    return body


class OpenAIStreamEncoder:
    """Turns domain stream events into `chat.completion.chunk` SSE frames."""

    def __init__(self, *, include_usage: bool, model: str) -> None:
        self._include_usage = include_usage
        self._id = f"chatcmpl-{uuid.uuid4().hex}"
        self._model = model
        self._created = 0

    def encode(self, event: ChatStreamEvent) -> list[str]:
        if isinstance(event, StreamStart):
            self._id, self._model, self._created = event.id, event.model, event.created
            return [self._chunk({"role": "assistant", "content": ""})]
        if isinstance(event, TextDelta):
            return [self._chunk({"content": event.text})]
        if isinstance(event, RefusalDelta):
            return [self._chunk({"refusal": event.text})]
        if isinstance(event, ToolCallDelta):
            call: dict[str, Any] = {"index": event.index}
            function: dict[str, Any] = {"arguments": event.arguments}
            if event.id is not None:
                call["id"] = event.id
                call["type"] = "function"
            if event.name is not None:
                function["name"] = event.name
            call["function"] = function
            return [self._chunk({"tool_calls": [call]})]
        frames = [self._chunk({}, finish_reason=event.finish_reason)]
        if self._include_usage and event.usage is not None:
            frames.append(sse_frame(self._envelope([], usage=usage_body(event.usage))))
        frames.append(sse_frame("[DONE]"))
        return frames

    def error(self, error: GatewayError) -> str:
        # Like the OpenAI API, an error frame ends the stream without [DONE].
        return sse_frame(error_body(error, anthropic=False))

    def _chunk(self, delta: dict[str, Any], *, finish_reason: str | None = None) -> str:
        choice = {"index": 0, "delta": delta, "finish_reason": finish_reason, "logprobs": None}
        return sse_frame(self._envelope([choice]))

    def _envelope(
        self, choices: list[dict[str, Any]], usage: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "id": self._id,
            "object": "chat.completion.chunk",
            "created": self._created,
            "model": self._model,
            "choices": choices,
        }
        if usage is not None:
            body["usage"] = usage
        return body
