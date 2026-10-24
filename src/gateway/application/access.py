"""Authentication and rate limiting of gateway clients."""

import math

from ..domain.clients import ClientIdentity
from ..domain.errors import AuthenticationError, RateLimitError
from .ports import ApiKeyVerifierPort, RateLimiterPort


class ClientAccess:
    def __init__(self, verifier: ApiKeyVerifierPort, limiter: RateLimiterPort) -> None:
        self._verifier = verifier
        self._limiter = limiter

    def authenticate(self, presented_key: str | None) -> ClientIdentity:
        if not presented_key:
            raise AuthenticationError(
                "Missing API key. Send your gateway key as 'Authorization: Bearer <key>' "
                "or 'x-api-key: <key>'.",
                code="missing_api_key",
            )
        client = self._verifier.verify(presented_key)
        if client is None:
            raise AuthenticationError("Invalid API key.")
        return client

    def authorize(self, presented_key: str | None) -> ClientIdentity:
        client = self.authenticate(presented_key)
        retry_after = self._limiter.acquire(client)
        if retry_after is not None:
            raise RateLimitError(
                f"Rate limit exceeded for client '{client.name}'. "
                f"Retry in {math.ceil(retry_after)} s.",
                retry_after=retry_after,
            )
        return client
