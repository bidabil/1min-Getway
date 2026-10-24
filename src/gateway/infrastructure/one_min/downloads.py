"""Download of generated files from the signed URLs (temporaryUrl) returned by 1min.ai."""

import ipaddress
from urllib.parse import urlsplit

import httpx

from ...domain.errors import PayloadTooLargeError, UpstreamError, UpstreamTimeoutError


class ResultDownloader:
    """Fetches result files. Only HTTPS, no redirects, no private addresses, size-capped.

    The shared HTTP client carries no default credentials, so the 1min.ai key is never sent
    to the storage host.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        allowed_host_suffixes: tuple[str, ...] = (),
        timeout_s: float = 120.0,
    ) -> None:
        self._client = client
        self._allowed = allowed_host_suffixes
        self._timeout = timeout_s

    async def download(self, url: str, *, max_bytes: int) -> tuple[bytes, str | None]:
        self._check_url(url)
        chunks: list[bytes] = []
        total = 0
        try:
            async with self._client.stream(
                "GET", url, timeout=self._timeout, follow_redirects=False
            ) as response:
                if response.status_code >= 400 or response.status_code in (301, 302, 303, 307, 308):
                    raise UpstreamError(
                        f"Could not download the generated file (HTTP {response.status_code})."
                    )
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise PayloadTooLargeError(
                            "The generated file is larger than MAX_DOWNLOAD_MB."
                        )
                    chunks.append(chunk)
                content_type = response.headers.get("content-type")
        except httpx.TimeoutException:
            raise UpstreamTimeoutError("Downloading the generated file timed out.") from None
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"Could not download the generated file ({type(exc).__name__})."
            ) from None
        return b"".join(chunks), content_type

    def _check_url(self, url: str) -> None:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if parts.scheme != "https" or not host:
            raise UpstreamError("Refusing to download a result that is not served over HTTPS.")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise UpstreamError("Refusing to download a result from a private address.")
        if self._allowed and not any(
            host == suffix or host.endswith(f".{suffix}") for suffix in self._allowed
        ):
            raise UpstreamError(f"Result host '{host}' is not in DOWNLOAD_ALLOWED_HOSTS.")
