"""Tool calling emulation for models served by the legacy Chat with AI API.

The legacy API has no function calling. The gateway describes the tools in the prompt and
asks the model to answer with `<tool_call>{"name": ..., "arguments": {...}}</tool_call>`
blocks, then parses them back into structured tool calls. Parsing is linear (no regex
backtracking) and only accepts tools that the client declared.
"""

import json
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ..chat import NamedToolChoice, ToolCall, ToolChoice, ToolDefinition

OPEN_TAG = "<tool_call>"
CLOSE_TAG = "</tool_call>"


def new_tool_call_id() -> str:
    return f"call_{uuid.uuid4().hex[:24]}"


def render_tool_instructions(
    tools: Iterable[ToolDefinition], tool_choice: ToolChoice | None
) -> str | None:
    tools = tuple(tools)
    if not tools or tool_choice == "none":
        return None

    lines = [
        "# Tools",
        "You can call the tools listed below. To call tools, reply with ONLY one block per call, "
        "in exactly this format and with no other text:",
        f'{OPEN_TAG}{{"name": "<tool name>", "arguments": {{<JSON object matching the tool parameters>}}}}{CLOSE_TAG}',
        "After your tool call blocks, STOP: never write tool results or an answer based on "
        "guessed results. The real results are given back to you in the next turn as "
        "<tool_result> entries; then use them to answer. Do not call the same tool again with "
        "the same arguments. If no tool is needed, answer normally.",
    ]
    if tool_choice == "required":
        lines.append("You MUST call at least one tool in this reply.")
    elif isinstance(tool_choice, NamedToolChoice):
        lines.append(f'You MUST call the tool "{tool_choice.name}" in this reply.')

    lines.append("")
    lines.append("Available tools (parameters are JSON Schema):")
    for tool in tools:
        header = f"- {tool.name}"
        if tool.description:
            header += f": {tool.description.strip()}"
        lines.append(header)
        parameters = json.dumps(dict(tool.parameters), ensure_ascii=False, separators=(",", ":"))
        lines.append(f"  parameters: {parameters}")
    return "\n".join(lines)


def format_tool_call(call: ToolCall) -> str:
    """Render a past tool call the way the model is asked to write them."""
    try:
        arguments: Any = json.loads(call.arguments) if call.arguments else {}
    except json.JSONDecodeError:
        arguments = call.arguments
    payload = json.dumps({"name": call.name, "arguments": arguments}, ensure_ascii=False)
    return f"{OPEN_TAG}{payload}{CLOSE_TAG}"


@dataclass(frozen=True, slots=True)
class ParsedReply:
    text: str | None
    tool_calls: tuple[ToolCall, ...]


def parse_tool_calls(
    text: str,
    tools: Iterable[ToolDefinition],
    *,
    id_factory: Callable[[], str] = new_tool_call_id,
) -> ParsedReply:
    """Extract tool call blocks from a model reply.

    Blocks naming an undeclared tool, or whose JSON is invalid, are ignored. When calls are
    found, only the text before the first one is kept: models sometimes go on to invent the
    tool results and an answer based on them, which must not reach the client.
    """
    allowed = {tool.name for tool in tools}
    calls: list[ToolCall] = []
    preamble_end: int | None = None
    position = 0
    while True:
        start = text.find(OPEN_TAG, position)
        if start < 0:
            break
        end = text.find(CLOSE_TAG, start + len(OPEN_TAG))
        if end < 0:
            break
        call = _decode_call(text[start + len(OPEN_TAG) : end], allowed, id_factory)
        if call is not None:
            calls.append(call)
            if preamble_end is None:
                preamble_end = start
        position = end + len(CLOSE_TAG)

    if not calls or preamble_end is None:
        return ParsedReply(text, ())
    preamble = text[:preamble_end]
    if not _strip_fences(preamble).strip():
        return ParsedReply(None, tuple(calls))
    return ParsedReply(_strip_fences(preamble).strip(), tuple(calls))


def _decode_call(body: str, allowed: set[str], id_factory: Callable[[], str]) -> ToolCall | None:
    try:
        payload = json.loads(_strip_fences(body).strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    name = payload.get("name")
    if not isinstance(name, str) or name not in allowed:
        return None
    raw_arguments: Any = next(
        (payload[key] for key in ("arguments", "parameters", "input") if key in payload), {}
    )
    if isinstance(raw_arguments, str):
        try:
            raw_arguments = json.loads(raw_arguments) if raw_arguments.strip() else {}
        except json.JSONDecodeError:
            return None
    if not isinstance(raw_arguments, Mapping):
        return None
    return ToolCall(
        id=id_factory(),
        name=name,
        arguments=json.dumps(raw_arguments, ensure_ascii=False),
    )


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that models sometimes wrap around blocks."""
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines)
