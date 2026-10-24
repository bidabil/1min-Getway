"""Pure ASGI middleware (safe with streaming responses)."""

import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ...domain.errors import PayloadTooLargeError
from ...infrastructure.observability.logging import client_var, request_id_var
from ...infrastructure.observability.metrics import GatewayMetrics
from .errors import error_response, is_anthropic_request

logger = logging.getLogger("gateway.access")

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestContextMiddleware:
    """Request id, access log (path only, never query strings or bodies) and HTTP metrics."""

    def __init__(self, app: ASGIApp, metrics: GatewayMetrics) -> None:
        self._app = app
        self._metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        inbound = Headers(scope=scope).get("x-request-id", "")
        request_id = inbound if _REQUEST_ID.match(inbound) else uuid.uuid4().hex
        request_token = request_id_var.set(request_id)
        client_token = client_var.set(None)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message).append("X-Request-ID", request_id)
            await send(message)

        try:
            await self._app(scope, receive, send_with_id)
        finally:
            duration = time.perf_counter() - started
            route = scope.get("route")
            route_path = getattr(route, "path", None) or "unmatched"
            self._metrics.observe_http(scope["method"], route_path, status, duration)
            state = scope.get("state") or {}
            logger.info(
                "%s %s %s",
                scope["method"],
                scope["path"],
                status,
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status,
                    "duration_ms": round(duration * 1000),
                    "client_name": state.get("client"),
                },
            )
            client_var.reset(client_token)
            request_id_var.reset(request_token)


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        declared = headers.get("content-length", "")
        error = PayloadTooLargeError(
            f"Request body exceeds {self._max_bytes // (1024 * 1024)} MiB."
        )
        if declared.isdigit() and int(declared) > self._max_bytes:
            anthropic = is_anthropic_request(scope["path"], headers)
            await error_response(error, anthropic=anthropic)(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max_bytes:
                    raise error
            return message

        await self._app(scope, limited_receive, send)
