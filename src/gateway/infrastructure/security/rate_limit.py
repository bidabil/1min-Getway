"""In-memory token-bucket rate limiter, one bucket per gateway client.

State is per process: with several workers or replicas each keeps its own buckets.
1min.ai itself limits the OpenAI-compatible API to 60 requests per minute per account.
"""

import time
from collections.abc import Callable

from ...domain.clients import ClientIdentity


class TokenBucketLimiter:
    def __init__(self, default_rpm: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._default_rpm = default_rpm
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}

    def acquire(self, client: ClientIdentity) -> float | None:
        rpm = (
            client.requests_per_minute
            if client.requests_per_minute is not None
            else self._default_rpm
        )
        if rpm <= 0:
            return None
        rate = rpm / 60.0
        now = self._clock()
        tokens, updated = self._buckets.get(client.name, (float(rpm), now))
        tokens = min(float(rpm), tokens + (now - updated) * rate)
        if tokens >= 1.0:
            self._buckets[client.name] = (tokens - 1.0, now)
            return None
        self._buckets[client.name] = (tokens, now)
        return (1.0 - tokens) / rate
