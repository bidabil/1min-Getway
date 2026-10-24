"""OpenAI-compatible media endpoints: images, audio and files."""

import json
import time
from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from ....bootstrap import Container
from ....domain.clients import ClientIdentity
from ....domain.errors import InvalidRequestError
from ....domain.media import (
    FileUpload,
    ImageEditRequest,
    ImageGenerationRequest,
    ImageResult,
    ImageVariationRequest,
    SpeechRequest,
    TranscriptionRequest,
    UploadedAsset,
)
from ..dependencies import client_identity, get_container, json_body
from ..translators.common import as_int, as_mapping, as_str

router = APIRouter(tags=["OpenAI"])

_TRANSCRIPTION_FORMATS = ("json", "text", "srt", "verbose_json", "vtt")
_IMAGE_RESPONSE_FORMATS = ("url", "b64_json")


@router.post("/v1/images/generations")
async def images_generations(
    request: Request,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    body = await json_body(request)
    response_format = _image_response_format(body.get("response_format"))
    result = await container.images.generate(
        ImageGenerationRequest(
            prompt=as_str(body.get("prompt"), "prompt", required=True) or "",
            model=as_str(body.get("model"), "model") or container.settings.default_image_model,
            n=as_int(body.get("n"), "n", minimum=1),
            size=as_str(body.get("size"), "size"),
            quality=as_str(body.get("quality"), "quality"),
            style=as_str(body.get("style"), "style"),
            background=as_str(body.get("background"), "background"),
            output_format=as_str(body.get("output_format"), "output_format"),
            extra=dict(as_mapping(body.get("prompt_object"), "prompt_object") or {}),
        ),
        base64_output=response_format == "b64_json",
    )
    return _image_body(result)


@router.post("/v1/images/edits")
async def images_edits(
    image: Annotated[UploadFile, File()],
    prompt: Annotated[str, Form()],
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
    mask: Annotated[UploadFile | None, File()] = None,
    model: Annotated[str | None, Form()] = None,
    n: Annotated[int | None, Form()] = None,
    size: Annotated[str | None, Form()] = None,
    quality: Annotated[str | None, Form()] = None,
    response_format: Annotated[str | None, Form()] = None,
    prompt_object: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    source = await _upload(container, image)
    mask_asset = await _upload(container, mask) if mask is not None else None
    result = await container.images.edit(
        ImageEditRequest(
            image=source.reference,
            prompt=prompt,
            model=model or "gpt-image-2",
            mask=mask_asset.reference if mask_asset else None,
            n=n,
            size=size,
            quality=quality,
            extra=_json_form(prompt_object, "prompt_object"),
        ),
        base64_output=_image_response_format(response_format) == "b64_json",
    )
    return _image_body(result)


@router.post("/v1/images/variations")
async def images_variations(
    image: Annotated[UploadFile, File()],
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
    model: Annotated[str | None, Form()] = None,
    n: Annotated[int | None, Form()] = None,
    size: Annotated[str | None, Form()] = None,
    response_format: Annotated[str | None, Form()] = None,
    prompt_object: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    source = await _upload(container, image)
    result = await container.images.vary(
        ImageVariationRequest(
            image=source.reference,
            model=model or "magic-art",
            n=n,
            size=size,
            extra=_json_form(prompt_object, "prompt_object"),
        ),
        base64_output=_image_response_format(response_format) == "b64_json",
    )
    return _image_body(result)


@router.post("/v1/audio/speech")
async def audio_speech(
    request: Request,
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
) -> Response:
    body = await json_body(request)
    speed = body.get("speed")
    if speed is not None and (isinstance(speed, bool) or not isinstance(speed, int | float)):
        raise InvalidRequestError("'speed' must be a number.", param="speed")
    result = await container.audio.speech(
        SpeechRequest(
            text=as_str(body.get("input"), "input", required=True) or "",
            model=as_str(body.get("model"), "model") or container.settings.default_tts_model,
            voice=as_str(body.get("voice"), "voice") or "alloy",
            response_format=as_str(body.get("response_format"), "response_format") or "mp3",
            speed=float(speed) if speed is not None else None,
            extra=dict(as_mapping(body.get("prompt_object"), "prompt_object") or {}),
        )
    )
    return Response(content=result.audio, media_type=result.content_type)


@router.post("/v1/audio/transcriptions")
async def audio_transcriptions(
    file: Annotated[UploadFile, File()],
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
    model: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form()] = None,
    prompt: Annotated[str | None, Form()] = None,
    response_format: Annotated[str | None, Form()] = None,
    temperature: Annotated[float | None, Form()] = None,
) -> Response:
    response_format = response_format or "json"
    if response_format not in _TRANSCRIPTION_FORMATS:
        raise InvalidRequestError(
            f"'response_format' must be one of {', '.join(_TRANSCRIPTION_FORMATS)}.",
            param="response_format",
        )
    asset = await _upload(container, file)
    result = await container.audio.transcribe(
        TranscriptionRequest(
            audio=asset.reference,
            model=model or container.settings.default_stt_model,
            language=language,
            prompt=prompt,
            response_format=response_format,
            temperature=temperature,
        )
    )
    if response_format == "json":
        return JSONResponse({"text": result.text})
    if response_format == "verbose_json":
        raw = result.raw if isinstance(result.raw, Mapping) else _maybe_json(result.text)
        return JSONResponse(raw if isinstance(raw, Mapping) else {"text": result.text})
    return PlainTextResponse(result.text)


@router.post("/v1/files")
async def files_upload(
    file: Annotated[UploadFile, File()],
    _client: ClientIdentity = Depends(client_identity),
    container: Container = Depends(get_container),
    purpose: Annotated[str, Form()] = "user_data",
) -> dict[str, Any]:
    asset = await _upload(container, file)
    return {
        "id": asset.reference,
        "object": "file",
        "bytes": asset.size,
        "created_at": int(time.time()),
        "filename": asset.filename,
        "purpose": purpose,
        "status": "processed",
        "asset_key": asset.key,
        "file_id": asset.file_id,
        "content_type": asset.content_type,
    }


async def _upload(container: Container, upload: UploadFile) -> UploadedAsset:
    content = await upload.read()
    return await container.files.upload(
        FileUpload(
            filename=upload.filename or "upload.bin",
            content=content,
            content_type=upload.content_type or "application/octet-stream",
        )
    )


def _image_response_format(value: Any) -> str:
    response_format = value or "url"
    if response_format not in _IMAGE_RESPONSE_FORMATS:
        raise InvalidRequestError(
            "'response_format' must be 'url' or 'b64_json'.", param="response_format"
        )
    return str(response_format)


def _image_body(result: ImageResult) -> dict[str, Any]:
    data = []
    for image in result.images:
        item: dict[str, Any] = {"asset_key": image.asset_key}
        if image.url:
            item["url"] = image.url
        if image.b64_json:
            item["b64_json"] = image.b64_json
        data.append(item)
    return {"created": result.created, "data": data, "record_id": result.record_id}


def _json_form(value: str | None, param: str) -> dict[str, Any]:
    if not value:
        return {}
    parsed = _maybe_json(value)
    if not isinstance(parsed, dict):
        raise InvalidRequestError(f"'{param}' must be a JSON object.", param=param)
    return parsed


def _maybe_json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None
