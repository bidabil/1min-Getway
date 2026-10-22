"""Render a stateless conversation into a single prompt for the legacy Chat with AI API.

The legacy API receives one prompt per call. Instead of relying on server-side
conversation state (which breaks with system prompts, restarts or several workers),
the gateway sends the whole conversation every time, like the OpenAI API does.
"""

from collections.abc import Mapping, Sequence

from ..chat import FilePart, ImagePart, Message, TextPart
from .tool_protocol import format_tool_call

CONTINUE_INSTRUCTION = "Continue the conversation: write the next assistant message."


def render_prompt(
    messages: Sequence[Message],
    *,
    tool_instructions: str | None = None,
    image_labels: Mapping[ImagePart, int] | None = None,
) -> str:
    labels = image_labels or {}
    instructions = [
        _render_content(message, labels).strip()
        for message in messages
        if message.role in ("system", "developer")
    ]
    if tool_instructions:
        instructions.append(tool_instructions)
    instructions = [block for block in instructions if block]
    turns = [message for message in messages if message.role not in ("system", "developer")]

    sections: list[str] = []
    if instructions:
        sections.append("<instructions>\n" + "\n\n".join(instructions) + "\n</instructions>")

    if len(turns) == 1 and turns[0].role == "user":
        sections.append(_render_content(turns[0], labels))
        return "\n\n".join(sections)

    tool_names = {call.id: call.name for message in turns for call in message.tool_calls}
    rendered_turns = [_render_turn(message, labels, tool_names) for message in turns]
    sections.append("<conversation>\n" + "\n".join(rendered_turns) + "\n</conversation>")
    sections.append(CONTINUE_INSTRUCTION)
    return "\n\n".join(sections)


def _render_turn(
    message: Message, labels: Mapping[ImagePart, int], tool_names: Mapping[str, str]
) -> str:
    body = _render_content(message, labels)
    if message.role == "assistant":
        calls = "\n".join(format_tool_call(call) for call in message.tool_calls)
        body = "\n".join(part for part in (body, calls) if part)
        return f"<assistant>\n{body}\n</assistant>"
    if message.role == "tool":
        name = message.name or tool_names.get(message.tool_call_id or "", "tool")
        status = ' status="error"' if message.is_error else ""
        return f'<tool_result name="{name}" id="{message.tool_call_id or ""}"{status}>\n{body}\n</tool_result>'
    return f"<user>\n{body}\n</user>"


def _render_content(message: Message, labels: Mapping[ImagePart, int]) -> str:
    pieces: list[str] = []
    for part in message.content:
        if isinstance(part, TextPart):
            pieces.append(part.text)
        elif isinstance(part, ImagePart):
            label = labels.get(part)
            pieces.append(f"[image {label}]" if label is not None else "[image]")
        elif isinstance(part, FilePart):
            pieces.append(f"[file {part.filename}]" if part.filename else "[file]")
    return "\n".join(piece for piece in pieces if piece)
