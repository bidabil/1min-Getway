"""Adapter for the 1min.ai AI Feature API and Get Result API."""

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from ...domain.errors import UpstreamError
from ...domain.features import FeatureRecord, FeatureRequest, FeatureStatus
from .http import OneMinHttp

FEATURES_PATH = "/api/features"
RESULTS_PATH = "/api/results/{id}"

_STATUSES = {
    "SUCCESS": FeatureStatus.SUCCEEDED,
    "SUCCEEDED": FeatureStatus.SUCCEEDED,
    "COMPLETED": FeatureStatus.SUCCEEDED,
    "PROCESSING": FeatureStatus.PROCESSING,
    "PENDING": FeatureStatus.PROCESSING,
    "QUEUED": FeatureStatus.PROCESSING,
    "IN_PROGRESS": FeatureStatus.PROCESSING,
    "FAILED": FeatureStatus.FAILED,
    "FAILURE": FeatureStatus.FAILED,
    "ERROR": FeatureStatus.FAILED,
}


class FeatureClient:
    def __init__(self, http: OneMinHttp, *, timeout_s: float, poll_timeout_s: float = 30.0) -> None:
        self._http = http
        self._timeout = timeout_s
        self._poll_timeout = poll_timeout_s

    async def run(self, request: FeatureRequest) -> FeatureRecord:
        data = await self._http.post_json(
            FEATURES_PATH, build_payload(request), auth="api_key", timeout_s=self._timeout
        )
        record = data.get("aiRecord") if isinstance(data, dict) else None
        if not isinstance(record, dict):
            raise UpstreamError("1min.ai returned a feature response without aiRecord.")
        return parse_record(record, request)

    async def get_result(self, record_id: str) -> FeatureRecord | None:
        data = await self._http.get_json(
            RESULTS_PATH.format(id=quote(record_id, safe="")),
            auth="api_key",
            timeout_s=self._poll_timeout,
        )
        record = data.get("aiRecord") if isinstance(data, dict) else None
        if not isinstance(record, dict):
            return None
        return parse_record(record, None)


def build_payload(request: FeatureRequest) -> dict[str, Any]:
    payload: dict[str, Any] = dict(request.extra)
    payload.update(type=request.type, model=request.model, promptObject=dict(request.prompt_object))
    if request.conversation_id:
        payload["conversationId"] = request.conversation_id
    if request.run_async:
        payload["async"] = True
    return payload


def parse_record(record: Mapping[str, Any], request: FeatureRequest | None) -> FeatureRecord:
    detail = record.get("aiRecordDetail")
    result = detail.get("resultObject") if isinstance(detail, Mapping) else None
    status = _STATUSES.get(str(record.get("status") or "").upper())
    error: Mapping[str, Any] | None = None
    results: tuple[Any, ...] = ()
    if isinstance(result, list):
        results = tuple(result)
    elif isinstance(result, Mapping):
        error = result
    elif isinstance(result, str) and result:
        results = (result,)
    if status is None:
        status = FeatureStatus.SUCCEEDED if results else FeatureStatus.PROCESSING
    if status is FeatureStatus.FAILED and error is None and results:
        error = {"message": str(results[0])}
    return FeatureRecord(
        id=str(record.get("uuid") or ""),
        type=str(record.get("type") or (request.type if request else "")),
        model=str(record.get("model") or (request.model if request else "")),
        status=status,
        results=results,
        temporary_url=record.get("temporaryUrl")
        if isinstance(record.get("temporaryUrl"), str)
        else None,
        created_at=record.get("createdAt") if isinstance(record.get("createdAt"), str) else None,
        error=error,
    )
