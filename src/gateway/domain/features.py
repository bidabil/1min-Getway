"""1min.ai "AI features" (image, audio, video, writing, code tools)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal

_EMPTY: Mapping[str, Any] = MappingProxyType({})


class FeatureStatus(Enum):
    SUCCEEDED = "succeeded"
    PROCESSING = "processing"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class FeatureRequest:
    type: str
    model: str
    prompt_object: Mapping[str, Any]
    run_async: bool = False
    conversation_id: str | None = None
    extra: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)


@dataclass(frozen=True, slots=True)
class FeatureRecord:
    id: str
    type: str
    model: str
    status: FeatureStatus
    results: tuple[Any, ...] = ()
    temporary_url: str | None = None
    created_at: str | None = None
    error: Mapping[str, Any] | None = None

    @property
    def done(self) -> bool:
        return self.status is not FeatureStatus.PROCESSING

    def first_text(self) -> str | None:
        for item in self.results:
            if isinstance(item, str):
                return item
            if isinstance(item, Mapping):
                for key in ("text", "content", "result", "transcript"):
                    value = item.get(key)
                    if isinstance(value, str):
                        return value
        return None


@dataclass(frozen=True, slots=True)
class FeatureField:
    name: str
    type: str
    required: bool = False
    description: str | None = None
    enum: tuple[str, ...] = ()
    default: Any = None


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    """Catalog entry describing a feature type, for discovery and tool descriptions."""

    type: str
    category: str
    title: str
    description: str
    models: tuple[str, ...] = ()
    fields: tuple[FeatureField, ...] = ()
    conversation_id: Literal["type", "none"] = "none"
    long_running: bool = False
    docs_url: str | None = None
