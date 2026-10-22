"""Rendering of domain errors in the OpenAI or Anthropic error format."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException

from ...domain.errors import (
    ErrorKind,
    GatewayError,
    InvalidRequestError,
    NotFoundError,
    PayloadTooLargeError,
)

logger = logging.getLogger(__name__)

HTTP_STATUS = {
    ErrorKind.INVALID_REQUEST: 400,
    ErrorKind.AUTHENTICATION: 401,
    ErrorKind.PERMISSION: 403,
    ErrorKind.NOT_FOUND: 404,
    ErrorKind.PAYLOAD_TOO_LARGE: 413,
    ErrorKind.RATE_LIMITED: 429,
    ErrorKind.UPSTREAM: 502,
    ErrorKind.UPSTREAM_TIMEOUT: 504,
    ErrorKind.UNAVAILABLE: 503,
    ErrorKind.INTERNAL: 500,
}

OPENAI_TYPES = {
    ErrorKind.INVALID_REQUEST: "invalid_request_error",
    ErrorKind.AUTHENTICATION: "authentication_error",
    ErrorKind.PERMISSION: "permission_error",
    ErrorKind.NOT_FOUND: "not_found_error",
    ErrorKind.PAYLOAD_TOO_LARGE: "invalid_request_error",
    ErrorKind.RATE_LIMITED: "rate_limit_error",
    ErrorKind.UPSTREAM: "api_error",
    ErrorKind.UPSTREAM_TIMEOUT: "timeout_error",
    ErrorKind.UNAVAILABLE: "api_error",
    ErrorKind.INTERNAL: "api_error",
}

ANTHROPIC_TYPES = {
    ErrorKind.INVALID_REQUEST: "invalid_request_error",
    ErrorKind.AUTHENTICATION: "authentication_error",
    ErrorKind.PERMISSION: "permission_error",
    ErrorKind.NOT_FOUND: "not_found_error",
    ErrorKind.PAYLOAD_TOO_LARGE: "request_too_large",
    ErrorKind.RATE_LIMITED: "rate_limit_error",
    ErrorKind.UPSTREAM: "api_error",
    ErrorKind.UPSTREAM_TIMEOUT: "api_error",
    ErrorKind.UNAVAILABLE: "overloaded_error",
    ErrorKind.INTERNAL: "api_error",
}


def is_anthropic_request(path: str, headers: Headers) -> bool:
    return path.startswith("/v1/messages") or "anthropic-version" in headers


def error_body(error: GatewayError, *, anthropic: bool) -> dict[str, Any]:
    if anthropic:
        return {
            "type": "error",
            "error": {"type": ANTHROPIC_TYPES[error.kind], "message": error.message},
        }
    return {
        "error": {
            "message": error.message,
            "type": OPENAI_TYPES[error.kind],
            "param": error.param,
            "code": error.code,
        }
    }


def error_response(error: GatewayError, *, anthropic: bool) -> JSONResponse:
    headers: dict[str, str] = {}
    if error.retry_after is not None:
        headers["Retry-After"] = str(max(1, round(error.retry_after)))
    if error.upstream_request_id:
        headers["X-Upstream-Request-Id"] = error.upstream_request_id
    if error.kind is ErrorKind.AUTHENTICATION:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        error_body(error, anthropic=anthropic), status_code=HTTP_STATUS[error.kind], headers=headers
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GatewayError)
    async def handle_gateway_error(request: Request, exc: GatewayError) -> JSONResponse:
        if exc.kind in (ErrorKind.UPSTREAM, ErrorKind.UPSTREAM_TIMEOUT, ErrorKind.INTERNAL):
            logger.warning(
                "Request failed: %s",
                exc.message,
                extra={"error_code": exc.code, "upstream_request_id": exc.upstream_request_id},
            )
        return error_response(
            exc, anthropic=is_anthropic_request(request.url.path, request.headers)
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(
            str(part) for part in first.get("loc", ()) if part not in ("body", "query", "path")
        )
        message = (
            f"{location}: {first.get('msg', 'invalid value')}" if location else "Invalid request."
        )
        error = InvalidRequestError(message, param=location or None)
        return error_response(
            error, anthropic=is_anthropic_request(request.url.path, request.headers)
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        error: GatewayError
        if exc.status_code == 404:
            error = NotFoundError(f"Unknown endpoint {request.method} {request.url.path}.")
        elif exc.status_code == 405:
            error = InvalidRequestError(
                f"Method {request.method} is not allowed on {request.url.path}.",
                code="method_not_allowed",
            )
        elif exc.status_code == 413:
            error = PayloadTooLargeError(str(exc.detail))
        else:
            error = InvalidRequestError(str(exc.detail))
        response = error_response(
            error, anthropic=is_anthropic_request(request.url.path, request.headers)
        )
        if exc.status_code == 405:
            response.status_code = 405
        return response

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        error = GatewayError("Internal gateway error.")
        return error_response(
            error, anthropic=is_anthropic_request(request.url.path, request.headers)
        )
