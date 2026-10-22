"""Provider-neutral chat model: messages, tools, results and streaming events."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

from .models import Backend

Role = Literal["system", "developer", "user", "assistant", "tool"]
FinishReason = Literal["stop", "length", "tool_calls", "content_filter", "error"]

_EMPTY: Mapping[str, Any] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class TextPart:
    text: str


@dataclass(frozen=True, slots=True)
class ImagePart:
    """An image given as an http(s) URL, a data: URI or a 1min.ai asset key."""

    url: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class FilePart:
    """A document given inline (data: URI) or by a 1min.ai file id."""

    data: str | None = None
    file_id: str | None = None
    filename: str | None = None


ContentPart = TextPart | ImagePart | FilePart


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text, exactly as produced by the model


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: tuple[ContentPart, ...] = ()
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    name: str | None = None
    is_error: bool = False

    def text(self) -> str:
        return "".join(part.text for part in self.content if isinstance(part, TextPart))

    def images(self) -> tuple[ImagePart, ...]:
        return tuple(part for part in self.content if isinstance(part, ImagePart))

    def files(self) -> tuple[FilePart, ...]:
        return tuple(part for part in self.content if isinstance(part, FilePart))


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)
    strict: bool | None = None


@dataclass(frozen=True, slots=True)
class NamedToolChoice:
    name: str


ToolChoice = Literal["auto", "none", "required"] | NamedToolChoice


@dataclass(frozen=True, slots=True)
class ResponseFormat:
    type: Literal["text", "json_object", "json_schema"]
    json_schema: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class GenerationOptions:
    max_output_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stop: tuple[str, ...] = ()
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    seed: int | None = None
    reasoning_effort: str | None = None
    response_format: ResponseFormat | None = None
    parallel_tool_calls: bool | None = None
    user: str | None = None


@dataclass(frozen=True, slots=True)
class WebSearch:
    enabled: bool = True
    sites: int | None = None
    max_words: int | None = None


@dataclass(frozen=True, slots=True)
class ChatRequest:
    model: str
    messages: tuple[Message, ...]
    tools: tuple[ToolDefinition, ...] = ()
    tool_choice: ToolChoice | None = None
    options: GenerationOptions = field(default_factory=GenerationOptions)
    web_search: WebSearch | None = None
    file_ids: tuple[str, ...] = ()
    include_usage: bool = False
    extra: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)

    def has_images(self) -> bool:
        return any(message.images() for message in self.messages)

    def has_files(self) -> bool:
        return bool(self.file_ids) or any(message.files() for message in self.messages)


@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int | None = None
    estimated: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class ChatResult:
    id: str
    model: str
    created: int
    text: str | None
    tool_calls: tuple[ToolCall, ...]
    finish_reason: FinishReason
    usage: Usage | None
    refusal: str | None = None
    backend: Backend | None = None


# --- Streaming events -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StreamStart:
    id: str
    model: str
    created: int
    backend: Backend | None = None


@dataclass(frozen=True, slots=True)
class TextDelta:
    text: str


@dataclass(frozen=True, slots=True)
class RefusalDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ToolCallDelta:
    """A fragment of a tool call. `id` and `name` are set on the first fragment of an index."""

    index: int
    arguments: str = ""
    id: str | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class StreamEnd:
    finish_reason: FinishReason
    usage: Usage | None = None


ChatStreamEvent = StreamStart | TextDelta | RefusalDelta | ToolCallDelta | StreamEnd
