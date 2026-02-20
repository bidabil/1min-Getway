"""
Network service for handling HTTP requests and responses.
"""

import logging
import uuid
from typing import Any

from fastapi import Response
from fastapi.responses import JSONResponse

from ..config import CORS_ORIGINS

logger = logging.getLogger("1min-gateway.network-service")


def _get_cors_origin() -> str:
    """
    Get the CORS origin header value.
    Returns empty string if CORS is not configured (blocks CORS requests).
    """
    return CORS_ORIGINS if CORS_ORIGINS else ""


def handle_options_request() -> Response:
    """
    Handle CORS preflight requests.
    """
    cors_origin = _get_cors_origin()
    headers: dict[str, str] = {
        "Access-Control-Allow-Headers": "Content-Type,API-KEY,Authorization",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "X-Request-ID": f"opt-{uuid.uuid4()}",
    }
    # Only add CORS origin header if configured
    if cors_origin:
        headers["Access-Control-Allow-Origin"] = cors_origin
    return Response(status_code=204, headers=headers)


def set_response_headers(response: Response) -> Response:
    """
    Apply standard security and tracking headers to JSON responses.
    """
    response.headers["Content-Type"] = "application/json"

    # Only add CORS header if configured
    cors_origin = _get_cors_origin()
    if cors_origin:
        response.headers["Access-Control-Allow-Origin"] = cors_origin

    # Unique Request ID for log correlation
    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id

    # Allow client-side apps to read custom headers
    response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"

    return response


def create_json_response(content: dict[str, Any], status_code: int = 200) -> JSONResponse:
    """
    Create a JSON response with standard headers.
    """
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Request-ID": str(uuid.uuid4()),
        "Access-Control-Expose-Headers": "X-Request-ID",
    }
    # Only add CORS header if configured
    cors_origin = _get_cors_origin()
    if cors_origin:
        headers["Access-Control-Allow-Origin"] = cors_origin
    return JSONResponse(content=content, status_code=status_code, headers=headers)
