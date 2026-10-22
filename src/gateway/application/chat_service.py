"""Chat completions: routes each request to the native or the legacy 1min.ai chat API."""

import time
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, replace

from ..domain.chat import (
    ChatRequest,
    ChatResult,
    ChatStreamEvent,
    FilePart,
    ImagePart,
    StreamEnd,
    StreamStart,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    Usage,
    WebSearch,
)
from ..domain.errors import InvalidRequestError
from ..domain.media import FileUpload
from ..domain.models import Backend
from ..domain.services.crawl_notices import CrawlNoticeFilter, strip_crawl_notices
from ..domain.services.data_uri import decode_data_uri, is_data_uri
from ..domain.services.routing import Route, choose_route
from ..domain.services.sampling import SamplingPolicy
from ..domain.services.tokens import estimate_tokens
from ..domain.services.tool_protocol import parse_tool_calls, render_tool_instructions
from ..domain.services.transcript import render_prompt
from .model_directory import ModelDirectory
from .ports import AssetStorePort, LegacyChatCall, LegacyChatPort, NativeChatPort


@dataclass(frozen=True, slots=True)
class ChatSettings:
    web_search_suffix: str = ":online"
    max_inline_bytes: int = 20 * 1024 * 1024
    max_legacy_images: int = 10
    strip_crawl_notices: bool = True


@dataclass(frozen=True, slots=True)
class _LegacyPlan:
    request: ChatRequest
    route: Route
    call: LegacyChatCall
    tools_active: bool


def _completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex}"


class ChatService:
    def __init__(
        self,
        *,
        native: NativeChatPort,
        legacy: LegacyChatPort,
        models: ModelDirectory,
        assets: AssetStorePort,
        policy: SamplingPolicy,
        settings: ChatSettings,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._native = native
        self._legacy = legacy
        self._models = models
        self._assets = assets
        self._policy = policy
        self._settings = settings
        self._clock = clock

    async def complete(self, request: ChatRequest) -> ChatResult:
        route = await self._route(request)
        if route.backend is Backend.NATIVE:
            result = await self._native.complete(self._native_request(request, route))
            return replace(result, backend=Backend.NATIVE)
        plan = await self._plan_legacy(request, route)
        text = await self._legacy.complete(plan.call)
        if self._settings.strip_crawl_notices:
            text = strip_crawl_notices(text)
        return self._legacy_result(plan, text, _completion_id())

    async def stream(self, request: ChatRequest) -> AsyncGenerator[ChatStreamEvent, None]:
        """Stream events. Errors raised before the first event mean nothing was sent yet."""
        route = await self._route(request)
        if route.backend is Backend.NATIVE:
            async for event in self._native.stream(self._native_request(request, route)):
                if isinstance(event, StreamStart):
                    event = replace(event, backend=Backend.NATIVE)
                yield event
            return

        plan = await self._plan_legacy(request, route)
        completion_id = _completion_id()
        chunks = aiter(self._legacy.stream(plan.call))
        # Wait for the first chunk before starting the stream, so that an upstream refusal
        # (unsupported model, invalid attachment...) is returned as a regular HTTP error.
        first = await anext(chunks, "")
        yield StreamStart(
            id=completion_id, model=route.model, created=int(self._clock()), backend=Backend.LEGACY
        )

        if plan.tools_active:
            # Tool calls can only be recognised once the whole reply is known.
            text = first + "".join([chunk async for chunk in chunks])
            if self._settings.strip_crawl_notices:
                text = strip_crawl_notices(text)
            result = self._legacy_result(plan, text, completion_id)
            if result.text:
                yield TextDelta(result.text)
            for index, call in enumerate(result.tool_calls):
                yield ToolCallDelta(
                    index=index, id=call.id, name=call.name, arguments=call.arguments
                )
            yield StreamEnd(result.finish_reason, result.usage)
            return

        notice_filter = CrawlNoticeFilter() if self._settings.strip_crawl_notices else None
        produced: list[str] = []

        async def remaining() -> AsyncGenerator[str, None]:
            if first:
                yield first
            async for chunk in chunks:
                yield chunk

        async for chunk in remaining():
            text = notice_filter.feed(chunk) if notice_filter else chunk
            if text:
                produced.append(text)
                yield TextDelta(text)
        if notice_filter and (tail := notice_filter.flush()):
            produced.append(tail)
            yield TextDelta(tail)
        yield StreamEnd("stop", self._estimate_usage(plan.call.prompt, "".join(produced)))

    # --- routing ------------------------------------------------------------------------

    async def _route(self, request: ChatRequest) -> Route:
        if not request.messages:
            raise InvalidRequestError(
                "'messages' must contain at least one message.", param="messages"
            )
        snapshot = await self._models.snapshot()
        return choose_route(request, snapshot, web_search_suffix=self._settings.web_search_suffix)

    def _native_request(self, request: ChatRequest, route: Route) -> ChatRequest:
        return replace(
            request,
            model=route.model,
            options=self._policy.apply(route.model, request.options),
            web_search=None,
            file_ids=(),
        )

    # --- legacy backend -----------------------------------------------------------------

    async def _plan_legacy(self, request: ChatRequest, route: Route) -> _LegacyPlan:
        if not any(message.role != "system" and message.content for message in request.messages):
            raise InvalidRequestError(
                "The conversation has no message with content.", param="messages"
            )

        images: list[str] = []
        labels: dict[ImagePart, int] = {}
        file_ids: list[str] = list(request.file_ids)
        for message in request.messages:
            for image in message.images():
                if image in labels:
                    continue
                if len(images) >= self._settings.max_legacy_images:
                    raise InvalidRequestError(
                        f"At most {self._settings.max_legacy_images} images are supported per request.",
                        param="messages",
                    )
                images.append(await self._image_reference(image))
                labels[image] = len(images)
            for file in message.files():
                file_ids.append(await self._file_reference(file))

        tool_instructions = render_tool_instructions(request.tools, request.tool_choice)
        prompt = render_prompt(
            request.messages, tool_instructions=tool_instructions, image_labels=labels
        )
        web_search = (
            request.web_search if request.web_search and request.web_search.enabled else None
        )
        if route.web_search and web_search is None:
            web_search = WebSearch()
        call = LegacyChatCall(
            model=route.model,
            prompt=prompt,
            images=tuple(images),
            file_ids=tuple(dict.fromkeys(file_ids)),
            web_search=web_search,
        )
        return _LegacyPlan(request, route, call, tools_active=tool_instructions is not None)

    async def _image_reference(self, image: ImagePart) -> str:
        if not is_data_uri(image.url):
            return image.url  # http(s) URL or asset key: 1min.ai fetches it itself
        decoded = decode_data_uri(
            image.url, max_bytes=self._settings.max_inline_bytes, param="messages"
        )
        asset = await self._assets.upload(
            FileUpload(f"image.{decoded.extension}", decoded.content, decoded.media_type)
        )
        return asset.reference

    async def _file_reference(self, file: FilePart) -> str:
        if file.file_id:
            return file.file_id
        if not file.data or not is_data_uri(file.data):
            raise InvalidRequestError(
                "File parts need a 'file_id' or inline base64 data.", param="messages"
            )
        decoded = decode_data_uri(
            file.data, max_bytes=self._settings.max_inline_bytes, param="messages"
        )
        name = file.filename or f"document.{decoded.extension}"
        asset = await self._assets.upload(FileUpload(name, decoded.content, decoded.media_type))
        return asset.file_id or asset.reference

    def _legacy_result(self, plan: _LegacyPlan, text: str, completion_id: str) -> ChatResult:
        content: str | None = text
        tool_calls: tuple[ToolCall, ...] = ()
        if plan.tools_active:
            parsed = parse_tool_calls(text, plan.request.tools)
            content, tool_calls = parsed.text, parsed.tool_calls
        return ChatResult(
            id=completion_id,
            model=plan.route.model,
            created=int(self._clock()),
            text=content,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
            usage=self._estimate_usage(plan.call.prompt, text),
            backend=Backend.LEGACY,
        )

    @staticmethod
    def _estimate_usage(prompt: str, completion: str) -> Usage:
        return Usage(
            prompt_tokens=estimate_tokens(prompt),
            completion_tokens=estimate_tokens(completion),
            estimated=True,
        )
