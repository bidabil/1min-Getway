"""
Network service for handling HTTP requests and responses.
"""

import logging
import uuid

from fastapi import Response
from fastapi.responses import JSONResponse

from ..config import CORS_ORIGINS

logger = logging.getLogger("1min-gateway.network-service")


def handle_options_request() -> Response:
    """
    Handle CORS preflight requests.
    """
    headers = {
        "Access-Control-Allow-Origin": CORS_ORIGINS,
        "Access-Control-Allow-Headers": "Content-Type,API-KEY,Authorization",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "X-Request-ID": f"opt-{uuid.uuid4()}",
    }
    return Response(status_code=204, headers=headers)


def set_response_headers(response: Response) -> Response:
    """
    Apply standard security and tracking headers to JSON responses.
    """
    response.headers["Content-Type"] = "application/json"
    response.headers["Access-Control-Allow-Origin"] = CORS_ORIGINS

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
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": CORS_ORIGINS,
        "X-Request-ID": str(uuid.uuid4()),
        "Access-Control-Expose-Headers": "X-Request-ID",
    }
    return JSONResponse(content=content, status_code=status_code, headers=headers)
