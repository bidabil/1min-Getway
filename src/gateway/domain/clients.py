"""Gateway clients (the agents that call the gateway with a gateway API key)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClientIdentity:
    name: str
    requests_per_minute: int | None = None  # None: use the gateway default
