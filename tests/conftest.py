import socket
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from gateway.bootstrap import Container, build_container
from gateway.config import Settings
from gateway.infrastructure.security.api_keys import hash_key
from gateway.interfaces.http.app import create_app
from tests.fakes import BASE_URL, UPSTREAM_KEY, FakeOneMin

CLIENT_KEY = "gw-test-agent-key"
OTHER_KEY = "gw-test-limited-key"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must never reach the network: every upstream is faked in memory."""
    real_connect = socket.socket.connect

    def guarded(self: socket.socket, address: Any) -> Any:
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "::1", "localhost") and not isinstance(address, str):
            raise RuntimeError(f"Network access attempted in tests: {address!r}")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "one_min_api_key": UPSTREAM_KEY,
        "one_min_base_url": BASE_URL,
        "gateway_api_keys": f"agent:{hash_key(CLIENT_KEY)},limited:{hash_key(OTHER_KEY)}:2",
        "feature_poll_interval_s": 0.01,
        "rate_limit_rpm": 600,
        "log_format": "text",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


@pytest.fixture
def fake() -> FakeOneMin:
    return FakeOneMin()


@pytest.fixture
def container_factory(fake: FakeOneMin) -> Callable[..., Container]:
    def build(**overrides: Any) -> Container:
        return build_container(make_settings(**overrides), transport=fake.transport)

    return build


@pytest.fixture
def client_factory(
    container_factory: Callable[..., Container],
) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def build(**overrides: Any) -> TestClient:
        client = TestClient(create_app(container=container_factory(**overrides)))
        client.__enter__()
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(client_factory: Callable[..., TestClient]) -> TestClient:
    return client_factory()


@pytest.fixture
def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {CLIENT_KEY}"}
