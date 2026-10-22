"""FastAPI dependencies: container access, client authentication, JSON body parsing."""

import json
from typing import Any

from fastapi import Depends, Request
from starlette.datastructures import Headers

from ...bootstrap import Container
from ...domain.clients import ClientIdentity
from ...domain.errors import InvalidRequestError
from ...infrastructure.observability.logging import client_var


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def extract_api_key(headers: Headers) -> str | None:
    authorization = headers.get("authorization")
    if authorization:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer" and credentials.strip():
            return credentials.strip()
    for header in ("x-api-key", "api-key"):
        value = headers.get(header)
        if value and value.strip():
            return value.strip()
    return None


def client_identity(
    request: Request, container: Container = Depends(get_container)
) -> ClientIdentity:
    client = container.access.authorize(extract_api_key(request.headers))
    client_var.set(client.name)
    request.state.client = client.name
    return client


async def json_body(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if not raw:
        raise InvalidRequestError("The request body must be a JSON object.")
    try:
        body = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise InvalidRequestError("The request body is not valid JSON.") from None
    if not isinstance(body, dict):
        raise InvalidRequestError("The request body must be a JSON object.")
    return body
