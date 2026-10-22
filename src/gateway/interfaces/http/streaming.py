"""Server-sent event responses for chat streams, shared by the OpenAI and Anthropic APIs."""

import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from typing import Protocol

from fastapi.responses import StreamingResponse

from ...domain.chat import ChatStreamEvent, StreamEnd, Usage
from ...domain.errors import GatewayError, UpstreamError

logger = logging.getLogger(__name__)


class StreamEncoder(Protocol):
    def encode(self, event: ChatStreamEvent) -> list[str]: ...

    def error(self, error: GatewayError) -> str: ...


CompletionCallback = Callable[[str, Usage | None], None]


async def open_stream(events: AsyncGenerator[ChatStreamEvent, None]) -> ChatStreamEvent:
    """Wait for the first event so that early failures become regular HTTP errors."""
    try:
        return await anext(events)
    except StopAsyncIteration:
        raise UpstreamError("1min.ai returned an empty stream.") from None


def sse_response(
    first: ChatStreamEvent,
    events: AsyncGenerator[ChatStreamEvent, None],
    encoder: StreamEncoder,
    on_complete: CompletionCallback,
) -> StreamingResponse:
    return StreamingResponse(
        _frames(first, events, encoder, on_complete),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _frames(
    first: ChatStreamEvent,
    events: AsyncGenerator[ChatStreamEvent, None],
    encoder: StreamEncoder,
    on_complete: CompletionCallback,
) -> AsyncIterator[str]:
    outcome = "ok"
    usage: Usage | None = None
    try:
        for frame in encoder.encode(first):
            yield frame
        async for event in events:
            if isinstance(event, StreamEnd):
                usage = event.usage
            for frame in encoder.encode(event):
                yield frame
    except GatewayError as exc:
        outcome = "error"
        logger.warning("Stream failed: %s", exc.message, extra={"error_code": exc.code})
        yield encoder.error(exc)
    except asyncio.CancelledError:
        outcome = "cancelled"  # client disconnected; closing the generator cancels upstream
        raise
    except Exception:
        outcome = "error"
        logger.exception("Unexpected error while streaming")
        yield encoder.error(GatewayError("Internal gateway error."))
    finally:
        await events.aclose()
        on_complete(outcome, usage)
