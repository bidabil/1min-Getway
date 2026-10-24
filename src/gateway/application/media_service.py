"""Images, speech, transcription and file uploads, built on the generic feature service."""

import base64
import time
from collections.abc import Callable

from ..domain.errors import InvalidRequestError, PayloadTooLargeError, UpstreamError
from ..domain.features import FeatureRecord, FeatureRequest
from ..domain.media import (
    FileUpload,
    GeneratedImage,
    ImageEditRequest,
    ImageGenerationRequest,
    ImageResult,
    ImageVariationRequest,
    SpeechRequest,
    SpeechResult,
    TranscriptionRequest,
    TranscriptionResult,
    UploadedAsset,
)
from ..domain.services.image_sizing import (
    edit_prompt_object,
    generation_prompt_object,
    variation_prompt_object,
)
from ..domain.services.speech import speech_prompt_object
from .feature_service import FeatureService, require_success
from .ports import AssetStorePort, DownloaderPort

AUDIO_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}


class FileService:
    def __init__(self, assets: AssetStorePort, *, max_bytes: int) -> None:
        self._assets = assets
        self._max_bytes = max_bytes

    async def upload(self, upload: FileUpload) -> UploadedAsset:
        if not upload.content:
            raise InvalidRequestError("The uploaded file is empty.", param="file")
        if len(upload.content) > self._max_bytes:
            raise PayloadTooLargeError(
                f"Files are limited to {self._max_bytes // (1024 * 1024)} MiB.", param="file"
            )
        return await self._assets.upload(upload)


class ImageService:
    def __init__(
        self,
        features: FeatureService,
        downloader: DownloaderPort,
        *,
        timeout_s: float,
        max_download_bytes: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._features = features
        self._downloader = downloader
        self._timeout = timeout_s
        self._max_download = max_download_bytes
        self._clock = clock

    async def generate(
        self, request: ImageGenerationRequest, *, base64_output: bool = False
    ) -> ImageResult:
        if not request.prompt.strip():
            raise InvalidRequestError("'prompt' is required.", param="prompt")
        feature = FeatureRequest(
            "IMAGE_GENERATOR", request.model, generation_prompt_object(request)
        )
        return await self._run(feature, base64_output)

    async def edit(self, request: ImageEditRequest, *, base64_output: bool = False) -> ImageResult:
        feature = FeatureRequest("IMAGE_EDITOR", request.model, edit_prompt_object(request))
        return await self._run(feature, base64_output)

    async def vary(
        self, request: ImageVariationRequest, *, base64_output: bool = False
    ) -> ImageResult:
        feature = FeatureRequest("IMAGE_VARIATOR", request.model, variation_prompt_object(request))
        return await self._run(feature, base64_output)

    async def _run(self, feature: FeatureRequest, base64_output: bool) -> ImageResult:
        record = require_success(
            await self._features.run_and_wait(feature, timeout_s=self._timeout)
        )
        return ImageResult(
            created=int(self._clock()),
            images=await self._images(record, base64_output),
            record_id=record.id,
        )

    async def _images(
        self, record: FeatureRecord, base64_output: bool
    ) -> tuple[GeneratedImage, ...]:
        keys = [item for item in record.results if isinstance(item, str)] or [""]
        images: list[GeneratedImage] = []
        for index, key in enumerate(keys):
            # 1min.ai returns one signed URL, for the first result only.
            url = record.temporary_url if index == 0 else None
            encoded = None
            if base64_output and url:
                content, _ = await self._downloader.download(url, max_bytes=self._max_download)
                encoded = base64.b64encode(content).decode("ascii")
            images.append(GeneratedImage(asset_key=key, url=url, b64_json=encoded))
        return tuple(images)


class AudioService:
    def __init__(
        self,
        features: FeatureService,
        downloader: DownloaderPort,
        *,
        timeout_s: float,
        max_download_bytes: int,
    ) -> None:
        self._features = features
        self._downloader = downloader
        self._timeout = timeout_s
        self._max_download = max_download_bytes

    async def speech_url(self, request: SpeechRequest) -> str:
        """Synthesize speech and return the signed URL of the audio file."""
        if not request.text.strip():
            raise InvalidRequestError("'input' is required.", param="input")
        feature = FeatureRequest("TEXT_TO_SPEECH", request.model, speech_prompt_object(request))
        record = require_success(
            await self._features.run_and_wait(feature, timeout_s=self._timeout)
        )
        if not record.temporary_url:
            raise UpstreamError("1min.ai returned no audio URL.", code="missing_result")
        return record.temporary_url

    async def speech(self, request: SpeechRequest) -> SpeechResult:
        url = await self.speech_url(request)
        audio, content_type = await self._downloader.download(url, max_bytes=self._max_download)
        fallback = AUDIO_CONTENT_TYPES.get(request.response_format, "application/octet-stream")
        if not content_type or content_type.startswith(("application/octet-stream", "binary/")):
            content_type = fallback
        return SpeechResult(audio=audio, content_type=content_type, url=url)

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        upstream_format = (
            "text" if request.response_format in ("json", "text") else request.response_format
        )
        prompt_object: dict[str, object] = {
            "audioUrl": request.audio,
            "response_format": upstream_format,
        }
        if request.language:
            prompt_object["language"] = request.language
        if request.prompt:
            prompt_object["prompt"] = request.prompt
        if request.temperature is not None:
            prompt_object["temperature"] = request.temperature
        feature = FeatureRequest("SPEECH_TO_TEXT", request.model, prompt_object)
        record = require_success(
            await self._features.run_and_wait(feature, timeout_s=self._timeout)
        )
        text = record.first_text()
        if text is None:
            raise UpstreamError("1min.ai returned no transcript.", code="missing_result")
        raw = record.results[0] if record.results else None
        return TranscriptionResult(text=text, raw=raw)
