"""Adapter for the 1min.ai Asset API (file uploads)."""

from typing import Any

from ...domain.errors import UpstreamError
from ...domain.media import FileUpload, UploadedAsset
from .http import OneMinHttp

ASSETS_PATH = "/api/assets"


class AssetStore:
    def __init__(self, http: OneMinHttp, *, timeout_s: float) -> None:
        self._http = http
        self._timeout = timeout_s

    async def upload(self, upload: FileUpload) -> UploadedAsset:
        data = await self._http.post_files(
            ASSETS_PATH,
            {"asset": (upload.filename, upload.content, upload.content_type)},
            timeout_s=self._timeout,
        )
        return parse_asset(data, upload)


def parse_asset(data: Any, upload: FileUpload) -> UploadedAsset:
    asset = data.get("asset") if isinstance(data, dict) else None
    content = data.get("fileContent") if isinstance(data, dict) else None
    asset = asset if isinstance(asset, dict) else {}
    content = content if isinstance(content, dict) else {}
    key = asset.get("key") or content.get("path")
    if not isinstance(key, str) or not key:
        raise UpstreamError("1min.ai did not return a key for the uploaded file.")
    return UploadedAsset(
        key=key,
        filename=str(asset.get("originalname") or content.get("name") or upload.filename),
        size=int(asset.get("size") or len(upload.content)),
        content_type=str(asset.get("mimetype") or asset.get("contentType") or upload.content_type),
        file_id=content.get("uuid") if isinstance(content.get("uuid"), str) else None,
        path=content.get("path") if isinstance(content.get("path"), str) else None,
        created_at=content.get("createdAt") if isinstance(content.get("createdAt"), str) else None,
    )
