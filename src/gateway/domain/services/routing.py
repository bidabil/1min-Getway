"""Choose which 1min.ai chat API serves a request."""

import re
from dataclasses import dataclass, field
from fnmatch import fnmatchcase

from ..chat import ChatRequest
from ..errors import InvalidRequestError, NotFoundError
from ..models import Backend

_WILDCARDS = frozenset("*?[")
# Provider-qualified ids such as "us.anthropic.claude-haiku-4-5-20251001-v1:0" (AWS Bedrock).
_BEDROCK_PREFIX = re.compile(r"^(?:[a-z]{2}\.)?anthropic\.")
_BEDROCK_SUFFIX = re.compile(r"-v\d+(?::\d+)?$")


@dataclass(frozen=True, slots=True)
class ModelAlias:
    """Maps a client-facing model id (exact or fnmatch pattern such as "claude-*") to a 1min model."""

    pattern: str
    target: str

    @property
    def is_pattern(self) -> bool:
        return any(char in _WILDCARDS for char in self.pattern)


def short_model_name(model_id: str) -> str:
    """Name an agent would use for a provider-qualified id (Bedrock Claude ids)."""
    return _BEDROCK_SUFFIX.sub("", _BEDROCK_PREFIX.sub("", model_id))


@dataclass(frozen=True, slots=True)
class ModelDirectorySnapshot:
    native: frozenset[str]
    legacy: frozenset[str]
    aliases: tuple[ModelAlias, ...] = ()
    native_known: bool = True
    legacy_known: bool = False
    text_only: frozenset[str] = frozenset()  # legacy models known not to accept images
    short_names: dict[str, str] = field(default_factory=dict)

    def resolve(self, model: str) -> str:
        for alias in self.aliases:
            if not alias.is_pattern and alias.pattern == model:
                return alias.target
        if model in self.native or model in self.legacy:
            return model
        for alias in self.aliases:
            if alias.is_pattern and fnmatchcase(model, alias.pattern):
                return alias.target
        return self.short_names.get(model, model)


def short_name_index(model_ids: frozenset[str]) -> dict[str, str]:
    """Map short names ("claude-haiku-4-5-20251001") to qualified ids, newest id first."""
    index: dict[str, str] = {}
    for model_id in sorted(model_ids, reverse=True):
        short = short_model_name(model_id)
        if short != model_id and short not in model_ids:
            index.setdefault(short, model_id)
    return index


@dataclass(frozen=True, slots=True)
class Route:
    backend: Backend
    model: str
    web_search: bool = False


def choose_route(
    request: ChatRequest,
    directory: ModelDirectorySnapshot,
    *,
    web_search_suffix: str = ":online",
) -> Route:
    """Route to the native OpenAI-compatible API whenever it can serve the request.

    The legacy Chat with AI API is used for what the native API cannot do (image or file
    input, web search) and for models it does not list (e.g. Claude, Gemini, Grok).
    """
    requested = request.model.strip()
    if not requested:
        raise InvalidRequestError("'model' is required.", param="model")

    web_search = request.web_search is not None and request.web_search.enabled
    if web_search_suffix and requested.endswith(web_search_suffix):
        requested = requested[: -len(web_search_suffix)]
        web_search = True

    model = directory.resolve(requested)

    if request.has_images() and model in directory.text_only:
        raise InvalidRequestError(
            f"The model '{model}' does not accept image input. "
            "Use a vision model (see GET /v1/models, field 'vision').",
            code="model_not_vision_capable",
            param="model",
        )
    if web_search or request.has_images() or request.has_files():
        if directory.legacy_known and model not in directory.legacy:
            raise NotFoundError(
                f"The model '{model}' is not available for image, file or web-search requests.",
                code="model_not_found",
                param="model",
            )
        return Route(Backend.LEGACY, model, web_search)
    if model in directory.native:
        return Route(Backend.NATIVE, model)
    if model in directory.legacy:
        return Route(Backend.LEGACY, model)
    if not directory.native_known:
        # The native catalog could not be fetched: let the upstream decide.
        return Route(Backend.NATIVE, model)
    if not directory.legacy_known:
        return Route(Backend.LEGACY, model)
    raise NotFoundError(
        f"The model '{model}' does not exist or is not available.",
        code="model_not_found",
        param="model",
    )
