"""Liveness, readiness, version and Prometheus metrics."""

import asyncio
import os
import secrets
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from .... import __version__
from ....bootstrap import Container
from ....domain.errors import AuthenticationError, NotFoundError
from ..dependencies import extract_api_key, get_container

router = APIRouter(tags=["Operations"])


@router.get("/")
async def root() -> dict[str, Any]:
    return {"name": "1min-gateway", "version": __version__, "status": "ok"}


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the process is up. Never calls 1min.ai."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(container: Container = Depends(get_container)) -> JSONResponse:
    """Readiness: the 1min.ai model catalog could be fetched (cached)."""
    try:
        snapshot = await asyncio.wait_for(container.models.snapshot(), timeout=10)
    except TimeoutError:
        return JSONResponse(
            {"status": "unavailable", "reason": "1min.ai did not answer"}, status_code=503
        )
    if not snapshot.native_known:
        return JSONResponse(
            {"status": "unavailable", "reason": "1min.ai model list unavailable"}, status_code=503
        )
    return JSONResponse({"status": "ready", "native_models": len(snapshot.native)})


@router.get("/v1/version")
async def version() -> dict[str, str | None]:
    return {"version": __version__, "commit": os.environ.get("APP_COMMIT")}


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request, container: Container = Depends(get_container)) -> Response:
    token = container.settings.metrics_token
    if token is None or not token.get_secret_value():
        raise NotFoundError("Metrics are disabled (set METRICS_TOKEN to enable them).")
    presented = extract_api_key(request.headers) or ""
    if not secrets.compare_digest(presented.encode(), token.get_secret_value().encode()):
        raise AuthenticationError("Invalid metrics token.")
    return Response(container.metrics.render(), media_type=container.metrics.content_type)
