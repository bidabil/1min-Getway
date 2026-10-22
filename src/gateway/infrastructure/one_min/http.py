"""Thin async HTTP client for 1min.ai.

POST requests are never retried: 1min.ai bills each generation, and a retried POST is a new,
billable generation. Only idempotent GETs are retried.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx

from ...domain.errors import UpstreamError, UpstreamTimeoutError
from .errors import raise_for_upstream_status

logger = logging.getLogger(__name__)

AuthStyle = Literal["api_key", "bearer"]


class OneMinHttp:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str,
        api_key: str,
        connect_timeout_s: float,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._connect_timeout = connect_timeout_s

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def _headers(self, auth: AuthStyle) -> dict[str, str]:
        if auth == "bearer":
            return {"Authorization": f"Bearer {self._api_key}"}
        return {"API-KEY": self._api_key}

    def _timeout(self, seconds: float) -> httpx.Timeout:
        return httpx.Timeout(seconds, connect=self._connect_timeout)

    async def post_json(
        self, path: str, payload: Mapping[str, Any], *, auth: AuthStyle, timeout_s: float
    ) -> Any:
        try:
            response = await self._client.post(
                self._url(path),
                json=payload,
                headers=self._headers(auth),
                timeout=self._timeout(timeout_s),
            )
        except httpx.TimeoutException:
            raise UpstreamTimeoutError("1min.ai did not answer in time.") from None
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Could not reach 1min.ai ({type(exc).__name__}).") from None
        raise_for_upstream_status(response)
        return _json(response)

    async def post_files(
        self, path: str, files: Mapping[str, tuple[str, bytes, str]], *, timeout_s: float
    ) -> Any:
        try:
            response = await self._client.post(
                self._url(path),
                files=dict(files),
                headers=self._headers("api_key"),
                timeout=self._timeout(timeout_s),
            )
        except httpx.TimeoutException:
            raise UpstreamTimeoutError("1min.ai did not answer in time.") from None
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Could not reach 1min.ai ({type(exc).__name__}).") from None
        raise_for_upstream_status(response)
        return _json(response)

    async def get_json(
        self, path: str, *, auth: AuthStyle, timeout_s: float, retries: int = 2
    ) -> Any:
        attempt = 0
        while True:
            try:
                response = await self._client.get(
                    self._url(path), headers=self._headers(auth), timeout=self._timeout(timeout_s)
                )
                if response.status_code in (502, 503, 504) and attempt < retries:
                    raise httpx.TransportError(f"HTTP {response.status_code}")
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt >= retries:
                    if isinstance(exc, httpx.TimeoutException):
                        raise UpstreamTimeoutError("1min.ai did not answer in time.") from None
                    raise UpstreamError(
                        f"Could not reach 1min.ai ({type(exc).__name__})."
                    ) from None
                attempt += 1
                await asyncio.sleep(0.5 * 2**attempt)
                continue
            raise_for_upstream_status(response)
            return _json(response)

    @asynccontextmanager
    async def stream_post(
        self, path: str, payload: Mapping[str, Any], *, auth: AuthStyle, timeout_s: float
    ) -> AsyncIterator[httpx.Response]:
        request = self._client.build_request(
            "POST",
            self._url(path),
            json=payload,
            headers=self._headers(auth),
            timeout=self._timeout(timeout_s),
        )
        try:
            response = await self._client.send(request, stream=True)
        except httpx.TimeoutException:
            raise UpstreamTimeoutError("1min.ai did not answer in time.") from None
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Could not reach 1min.ai ({type(exc).__name__}).") from None
        try:
            if response.status_code >= 400:
                await response.aread()
                raise_for_upstream_status(response)
            yield response
        finally:
            await response.aclose()


async def iter_lines(response: httpx.Response) -> AsyncIterator[str]:
    """Iterate response lines, converting transport failures into domain errors."""
    try:
        async for line in response.aiter_lines():
            yield line
    except httpx.TimeoutException:
        raise UpstreamTimeoutError("1min.ai stopped sending data.") from None
    except httpx.HTTPError as exc:
        raise UpstreamError(f"The 1min.ai stream was interrupted ({type(exc).__name__}).") from None


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        raise UpstreamError("1min.ai returned an invalid JSON response.") from None
