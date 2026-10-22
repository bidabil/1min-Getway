"""Map 1min.ai error responses to domain errors.

1min.ai uses two error formats: the OpenAI-compatible API returns
{"error": {"message", "type", "param", "code"}}, the other APIs return
{"success": false, "error": {"code", "message", "details"}}.
"""

from typing import Any

import httpx

from ...domain.errors import (
    GatewayError,
    InvalidRequestError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionDeniedError,
    RateLimitError,
    UpstreamError,
    UpstreamTimeoutError,
)

_MAX_MESSAGE = 500


def raise_for_upstream_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    raise upstream_error(response)


def upstream_error(response: httpx.Response) -> GatewayError:
    status = response.status_code
    message, code, param = _extract(response)
    request_id = response.headers.get("x-request-id")
    if status in (400, 422):
        return InvalidRequestError(
            message or "1min.ai rejected the request.",
            code=code or "invalid_request",
            param=param,
            upstream_request_id=request_id,
        )
    if status == 401:
        return UpstreamError(
            "1min.ai rejected the gateway's API key. Check ONE_MIN_API_KEY.",
            code="upstream_authentication_failed",
            upstream_request_id=request_id,
        )
    if status == 402 or (status == 429 and code in ("insufficient_quota", "INSUFFICIENT_CREDITS")):
        return RateLimitError(
            message or "Insufficient 1min.ai credits.",
            code="insufficient_quota",
            upstream_request_id=request_id,
        )
    if status == 403:
        return PermissionDeniedError(
            message or "1min.ai refused the request.", code=code, upstream_request_id=request_id
        )
    if status == 404:
        return NotFoundError(
            message or "Not found on 1min.ai.",
            code=code,
            param=param,
            upstream_request_id=request_id,
        )
    if status == 413:
        return PayloadTooLargeError(
            message or "Payload too large for 1min.ai.", upstream_request_id=request_id
        )
    if status == 429:
        return RateLimitError(
            message or "1min.ai rate limit reached.",
            code="upstream_rate_limited",
            retry_after=_retry_after(response),
            upstream_request_id=request_id,
        )
    if status in (408, 504, 524):
        return UpstreamTimeoutError(
            "1min.ai did not answer in time.", upstream_request_id=request_id
        )
    return UpstreamError(
        f"1min.ai returned HTTP {status}" + (f": {message}" if message else "."),
        upstream_request_id=request_id,
    )


def error_from_payload(payload: Any) -> GatewayError | None:
    """Build an error from an in-band error object (e.g. inside an SSE stream)."""
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if error is None:
        return None
    if isinstance(error, dict):
        message = str(error.get("message") or "1min.ai reported an error.")[:_MAX_MESSAGE]
        code = error.get("code")
        return UpstreamError(message, code=str(code) if code else None)
    return UpstreamError(str(error)[:_MAX_MESSAGE])


def _extract(response: httpx.Response) -> tuple[str | None, str | None, str | None]:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return (text[:_MAX_MESSAGE] or None), None, None
    if not isinstance(payload, dict):
        return None, None, None
    error = payload.get("error", payload)
    if not isinstance(error, dict):
        return str(error)[:_MAX_MESSAGE], None, None
    message = error.get("message")
    details = error.get("details")
    if isinstance(details, list) and details:
        rendered = "; ".join(
            f"{item.get('field')}: {item.get('message')}" if isinstance(item, dict) else str(item)
            for item in details[:5]
        )
        message = f"{message} ({rendered})" if message else rendered
    code = error.get("code") or error.get("type")
    param = error.get("param")
    return (
        str(message)[:_MAX_MESSAGE] if message else None,
        str(code) if code else None,
        str(param) if param else None,
    )


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
