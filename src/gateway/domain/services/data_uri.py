"""Decoding of inline `data:` URIs (base64 images and documents sent by clients)."""

import base64
import binascii
import math
from dataclasses import dataclass

from ..errors import InvalidRequestError, PayloadTooLargeError

_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/svg+xml": "svg",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/csv": "csv",
    "application/json": "json",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}


@dataclass(frozen=True, slots=True)
class DecodedData:
    content: bytes
    media_type: str

    @property
    def extension(self) -> str:
        return _EXTENSIONS.get(self.media_type, "bin")


def is_data_uri(value: str) -> bool:
    return value[:5].lower() == "data:"


def decode_data_uri(uri: str, *, max_bytes: int, param: str | None = None) -> DecodedData:
    header, separator, payload = uri.partition(",")
    if not separator or not is_data_uri(header):
        raise InvalidRequestError("Malformed data URI.", param=param)
    meta = header[5:].split(";")
    media_type = (meta[0] or "application/octet-stream").strip().lower()
    if "base64" not in (item.strip().lower() for item in meta[1:]):
        raise InvalidRequestError("Only base64 data URIs are supported.", param=param)

    # Reject oversized payloads before decoding them.
    if math.floor(len(payload) * 3 / 4) > max_bytes + 3:
        raise PayloadTooLargeError(
            f"Inline file exceeds the {max_bytes // (1024 * 1024)} MiB limit.", param=param
        )
    padded = payload.strip() + "=" * (-len(payload.strip()) % 4)
    try:
        content = base64.b64decode(padded, validate=False)
    except (binascii.Error, ValueError):
        raise InvalidRequestError("Invalid base64 data in data URI.", param=param) from None
    if len(content) > max_bytes:
        raise PayloadTooLargeError(
            f"Inline file exceeds the {max_bytes // (1024 * 1024)} MiB limit.", param=param
        )
    return DecodedData(content=content, media_type=media_type)
