"""Ports: what the application needs from infrastructure. Adapters implement these."""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from ..domain.chat import ChatRequest, ChatResult, ChatStreamEvent, WebSearch
from ..domain.clients import ClientIdentity
from ..domain.features import FeatureRecord, FeatureRequest, FeatureSpec
from ..domain.media import FileUpload, UploadedAsset
from ..domain.models import ModelInfo


class NativeChatPort(Protocol):
    """The 1min.ai OpenAI-compatible Chat Completions API."""

    async def complete(self, request: ChatRequest) -> ChatResult: ...

    def stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]: ...


@dataclass(frozen=True, slots=True)
class LegacyChatCall:
    model: str
    prompt: str
    images: tuple[str, ...] = ()
    file_ids: tuple[str, ...] = ()
    web_search: WebSearch | None = None


class LegacyChatPort(Protocol):
    """The 1min.ai Chat with AI API (one prompt in, text out)."""

    async def complete(self, call: LegacyChatCall) -> str: ...

    def stream(self, call: LegacyChatCall) -> AsyncIterator[str]: ...


class NativeModelSource(Protocol):
    async def list_models(self) -> Sequence[ModelInfo]: ...


class ModelCatalogPort(Protocol):
    """1min.ai's public model catalog: which models each feature accepts."""

    async def models_for(self, feature_type: str) -> Sequence[ModelInfo]: ...


class AssetStorePort(Protocol):
    async def upload(self, upload: FileUpload) -> UploadedAsset: ...


class FeaturePort(Protocol):
    async def run(self, request: FeatureRequest) -> FeatureRecord: ...

    async def get_result(self, record_id: str) -> FeatureRecord | None: ...


class DownloaderPort(Protocol):
    async def download(self, url: str, *, max_bytes: int) -> tuple[bytes, str | None]: ...


class FeatureCatalogPort(Protocol):
    def list(self) -> Sequence[FeatureSpec]: ...

    def get(self, feature_type: str) -> FeatureSpec | None: ...


class ApiKeyVerifierPort(Protocol):
    def verify(self, presented_key: str) -> ClientIdentity | None: ...


class RateLimiterPort(Protocol):
    def acquire(self, client: ClientIdentity) -> float | None:
        """Consume one request. Returns None when allowed, else seconds to wait."""
        ...
