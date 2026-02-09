"""
Network service for handling HTTP requests and responses.
"""

import logging
import uuid

from flask import make_response

from ..config import CORS_ORIGINS

logger = logging.getLogger("1min-gateway.network-service")


def handle_options_request():
    """
    Handle CORS preflight requests.
    """
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", CORS_ORIGINS)
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,API-KEY,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    # Unique ID for tracking
    response.headers["X-Request-ID"] = f"opt-{uuid.uuid4()}"

    return response, 204


def set_response_headers(response):
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
