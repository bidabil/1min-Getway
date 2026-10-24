"""Gateway API keys.

Only SHA-256 digests of the keys are configured (GATEWAY_API_KEYS="name:digest[:rpm],...").
Generate a key and its configuration line with `python -m gateway.cli create-key NAME`.
"""

import hashlib
import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ...domain.clients import ClientIdentity

KEY_PREFIX = "gw-"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^[A-Za-z0-9_.@-]{1,64}$")


def generate_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    # Keys are 256-bit random tokens, not passwords: brute force is infeasible, so a fast
    # hash is appropriate (a slow KDF would only add latency to every request).
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class KeyEntry:
    name: str
    digest: str
    requests_per_minute: int | None = None

    def to_config(self) -> str:
        suffix = f":{self.requests_per_minute}" if self.requests_per_minute is not None else ""
        return f"{self.name}:{self.digest}{suffix}"


def parse_key_entries(spec: str) -> list[KeyEntry]:
    entries: list[KeyEntry] = []
    for raw in (item.strip() for line in spec.splitlines() for item in line.split(",")):
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split(":")
        if len(parts) not in (2, 3):
            raise ValueError(f"Invalid gateway key entry '{raw}': expected name:sha256[:rpm].")
        name, digest = parts[0].strip(), parts[1].strip().lower()
        if not _NAME.match(name):
            raise ValueError(f"Invalid gateway key name '{name}'.")
        if not _DIGEST.match(digest):
            raise ValueError(
                f"Gateway key '{name}' must be configured as its SHA-256 digest (64 hex characters), "
                "not as the key itself."
            )
        rpm = None
        if len(parts) == 3:
            if not parts[2].strip().isdigit():
                raise ValueError(f"Invalid rate limit for gateway key '{name}'.")
            rpm = int(parts[2])
        entries.append(KeyEntry(name, digest, rpm))
    return entries


def load_key_entries(spec: str, file_path: str | None) -> list[KeyEntry]:
    entries = parse_key_entries(spec)
    if file_path:
        entries.extend(parse_key_entries(Path(file_path).read_text(encoding="utf-8")))
    names = [entry.name for entry in entries]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise ValueError(f"Duplicate gateway key names: {', '.join(sorted(duplicates))}.")
    return entries


class StaticApiKeyVerifier:
    def __init__(self, entries: Iterable[KeyEntry]) -> None:
        self._clients = {
            entry.digest: ClientIdentity(entry.name, entry.requests_per_minute) for entry in entries
        }

    def __len__(self) -> int:
        return len(self._clients)

    def verify(self, presented_key: str) -> ClientIdentity | None:
        return self._clients.get(hash_key(presented_key))
