"""Media requests and results (images, speech, transcription, files)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

_EMPTY: Mapping[str, Any] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class FileUpload:
    filename: str
    content: bytes
    content_type: str


@dataclass(frozen=True, slots=True)
class UploadedAsset:
    """An object stored by the 1min.ai Asset API.

    `key` is the storage key used as imageUrl/audioUrl in features and in chat attachments;
    `file_id` (fileContent.uuid) is the id expected by chat `attachments.files`.
    """

    key: str
    filename: str
    size: int
    content_type: str
    file_id: str | None = None
    path: str | None = None
    created_at: str | None = None

    @property
    def reference(self) -> str:
        return self.key or self.path or ""


@dataclass(frozen=True, slots=True)
class ImageGenerationRequest:
    prompt: str
    model: str
    n: int | None = None
    size: str | None = None
    quality: str | None = None
    style: str | None = None
    background: str | None = None
    output_format: str | None = None
    extra: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)


@dataclass(frozen=True, slots=True)
class ImageEditRequest:
    image: str  # asset key or URL
    prompt: str
    model: str
    mask: str | None = None
    n: int | None = None
    size: str | None = None
    quality: str | None = None
    extra: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)


@dataclass(frozen=True, slots=True)
class ImageVariationRequest:
    image: str  # asset key or URL
    model: str
    n: int | None = None
    size: str | None = None
    extra: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    asset_key: str
    url: str | None = None
    b64_json: str | None = None


@dataclass(frozen=True, slots=True)
class ImageResult:
    created: int
    images: tuple[GeneratedImage, ...]
    record_id: str


@dataclass(frozen=True, slots=True)
class SpeechRequest:
    text: str
    model: str
    voice: str
    response_format: str = "mp3"
    speed: float | None = None
    extra: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)


@dataclass(frozen=True, slots=True)
class SpeechResult:
    audio: bytes
    content_type: str
    url: str | None


@dataclass(frozen=True, slots=True)
class TranscriptionRequest:
    audio: str  # asset key
    model: str
    language: str | None = None
    prompt: str | None = None
    response_format: str = "json"
    temperature: float | None = None


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    text: str
    raw: Any = None
