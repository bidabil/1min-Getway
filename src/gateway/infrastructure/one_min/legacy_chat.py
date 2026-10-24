"""Adapter for the 1min.ai Chat with AI API (UNIFY_CHAT_WITH_AI).

Used for models the OpenAI-compatible API does not list, and for image/file input and web
search. Each call is stateless: the gateway sends the full conversation as one prompt.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

from ...application.ports import LegacyChatCall
from ...domain.errors import GatewayError, InvalidRequestError, UpstreamError
from .errors import error_from_payload
from .http import OneMinHttp, iter_lines
from .sse import iter_sse

CHAT_PATH = "/api/chat-with-ai"


class LegacyChatBackend:
    def __init__(self, http: OneMinHttp, *, timeout_s: float) -> None:
        self._http = http
        self._timeout = timeout_s

    async def complete(self, call: LegacyChatCall) -> str:
        data = await self._http.post_json(
            CHAT_PATH, build_payload(call), auth="api_key", timeout_s=self._timeout
        )
        return result_text(data)

    async def stream(self, call: LegacyChatCall) -> AsyncIterator[str]:
        async with self._http.stream_post(
            f"{CHAT_PATH}?isStreaming=true",
            build_payload(call),
            auth="api_key",
            timeout_s=self._timeout,
        ) as response:
            produced = False
            async for event in iter_sse(iter_lines(response)):
                if event.event == "done":
                    return
                if event.event == "error":
                    raise stream_error(_json_or_text(event.data))
                if event.event == "result":
                    if not produced:  # no incremental content was sent: use the final record
                        text = result_text(_json_or_text(event.data))
                        if text:
                            produced = True
                            yield text
                    continue
                text = content_text(event.data)
                if text:
                    produced = True
                    yield text


def stream_error(payload: Any) -> GatewayError:
    """Error from an `error` SSE event, e.g. {"error": "Model X is not supported for feature Y"}."""
    error = error_from_payload(payload) or UpstreamError(
        f"1min.ai reported a streaming error: {str(payload)[:300]}"
    )
    lowered = error.message.lower()
    if "not supported" in lowered or "invalid" in lowered:
        return InvalidRequestError(error.message, code="unsupported_request")
    return error


def build_payload(call: LegacyChatCall) -> dict[str, Any]:
    prompt_object: dict[str, Any] = {"prompt": call.prompt}
    if call.web_search is not None and call.web_search.enabled:
        prompt_object["settings"] = {
            "webSearchSettings": {
                "webSearch": True,
                "numOfSite": call.web_search.sites or 3,
                "maxWord": call.web_search.max_words or 1000,
            }
        }
    attachments: dict[str, list[str]] = {}
    if call.images:
        attachments["images"] = list(call.images)
    if call.file_ids:
        attachments["files"] = list(call.file_ids)
    if attachments:
        prompt_object["attachments"] = attachments
    return {"type": "UNIFY_CHAT_WITH_AI", "model": call.model, "promptObject": prompt_object}


def content_text(data: str) -> str:
    """Text of one `content` event. Tolerates JSON objects, JSON strings and raw text."""
    payload = _json_or_text(data)
    if isinstance(payload, dict):
        for key in ("content", "text", "result"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        return ""
    if isinstance(payload, str):
        return payload
    return data  # a bare JSON scalar such as `2024` is text, not a protocol error


def result_text(data: Any) -> str:
    if not isinstance(data, dict):
        return data if isinstance(data, str) else ""
    record = data.get("aiRecord")
    if not isinstance(record, dict):
        error = error_from_payload(data)
        if error is not None:
            raise error
        raise UpstreamError("1min.ai returned a response without aiRecord.")
    status = str(record.get("status") or "").upper()
    detail = record.get("aiRecordDetail") or {}
    result = detail.get("resultObject") if isinstance(detail, dict) else None
    if status in ("FAILED", "FAILURE", "ERROR"):
        message = result.get("message") if isinstance(result, dict) else None
        raise UpstreamError(
            f"1min.ai could not answer: {message or status}.", code="generation_failed"
        )
    if isinstance(result, list):
        return "".join(item for item in result if isinstance(item, str))
    if isinstance(result, str):
        return result
    return ""


def _json_or_text(data: str) -> Any:
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data
