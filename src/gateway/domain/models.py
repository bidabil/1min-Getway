"""Model catalog entities."""

from dataclasses import dataclass
from enum import Enum


class Backend(Enum):
    """Which 1min.ai API serves a chat request.

    NATIVE: the OpenAI-compatible endpoint (/openai/v1): native tools, JSON mode, text only.
    LEGACY: the Chat with AI endpoint (/api/chat-with-ai): any chat model, images, files,
    web search; tools are emulated by the gateway.
    """

    NATIVE = "native"
    LEGACY = "legacy"


@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    backend: Backend
    owned_by: str = "1min-ai"
    created: int = 0
    alias_of: str | None = None
    name: str | None = None
    vision: bool | None = None  # accepts image input (legacy API); None when unknown
    max_output_tokens: int | None = None
    deprecation_date: str | None = None
