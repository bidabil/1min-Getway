"""Server-Sent Events parsing (per the WHATWG spec, whitespace in data is preserved)."""

from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SSEEvent:
    event: str
    data: str


async def iter_sse(lines: AsyncIterator[str]) -> AsyncIterator[SSEEvent]:
    event_type = "message"
    data_lines: list[str] = []
    async for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        if not line:
            if data_lines:
                yield SSEEvent(event_type, "\n".join(data_lines))
            event_type, data_lines = "message", []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            event_type = value or "message"
        elif field == "data":
            data_lines.append(value)
    if data_lines:
        yield SSEEvent(event_type, "\n".join(data_lines))
