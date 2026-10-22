"""Per-model adjustment of generation options before calling the native API.

1min.ai rejects sampling parameters (temperature, top_p, stop, penalties) for OpenAI
reasoning models, DeepSeek and Z.AI, and rejects output limits above the model cap.
Agent frameworks often send these parameters by default, so the gateway adapts them
instead of failing the request.
"""

from dataclasses import dataclass, replace
from fnmatch import fnmatchcase
from typing import Any

from ..chat import GenerationOptions

DEFAULT_RESTRICTED_PATTERNS: tuple[str, ...] = (
    "o1*",
    "o3*",
    "o4*",
    "gpt-5*",
    "gpt-6*",
    "deepseek*",
    "glm*",
)


@dataclass(frozen=True, slots=True)
class OutputCap:
    pattern: str
    max_tokens: int


@dataclass(frozen=True, slots=True)
class SamplingPolicy:
    drop_restricted: bool = True
    restricted_patterns: tuple[str, ...] = DEFAULT_RESTRICTED_PATTERNS
    output_caps: tuple[OutputCap, ...] = (OutputCap("gpt-4o*", 16384),)
    default_output_cap: int = 32768

    def apply(self, model: str, options: GenerationOptions) -> GenerationOptions:
        updates: dict[str, Any] = {}
        if self.drop_restricted and _matches(model, self.restricted_patterns):
            updates.update(
                temperature=None,
                top_p=None,
                stop=(),
                presence_penalty=None,
                frequency_penalty=None,
            )
        cap = self.output_cap(model)
        if options.max_output_tokens is not None and options.max_output_tokens > cap:
            updates["max_output_tokens"] = cap
        return replace(options, **updates) if updates else options

    def output_cap(self, model: str) -> int:
        for cap in self.output_caps:
            if _matches(model, (cap.pattern,)):
                return cap.max_tokens
        return self.default_output_cap


def _matches(model: str, patterns: tuple[str, ...]) -> bool:
    candidates = {model.lower(), model.lower().rsplit("/", 1)[-1]}
    return any(
        fnmatchcase(candidate, pattern.lower()) for candidate in candidates for pattern in patterns
    )
