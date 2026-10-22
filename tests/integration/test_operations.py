from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from gateway.bootstrap import ConfigurationError, build_container
from gateway.interfaces.mcp.server import build_mcp_server
from tests.conftest import CLIENT_KEY, make_settings
from tests.fakes import FakeOneMin

MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}


class TestHealth:
    def test_public_endpoints(self, client: TestClient) -> None:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/").json()["status"] == "ok"
        assert "version" in client.get("/v1/version").json()
        ready = client.get("/ready")
        assert (ready.status_code, ready.json()["native_models"]) == (200, 3)

    def test_ready_reports_upstream_failure(self, client: TestClient, fake: FakeOneMin) -> None:
        fake.overrides["/openai/v1/models"] = httpx.Response(500, json={})
        assert client.get("/ready").status_code == 503

    def test_docs_disabled_by_default(
        self, client: TestClient, client_factory: Callable[..., TestClient]
    ) -> None:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client_factory(docs_enabled=True).get("/openapi.json").status_code == 200

    def test_metrics_require_token(
        self, client: TestClient, client_factory: Callable[..., TestClient], auth: dict[str, str]
    ) -> None:
        assert client.get("/metrics").status_code == 404
        secured = client_factory(metrics_token="m-token")
        assert secured.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
        secured.post(
            "/v1/chat/completions",
            headers=auth,
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]},
        )
        metrics = secured.get("/metrics", headers={"Authorization": "Bearer m-token"})
        assert metrics.status_code == 200
        assert metrics.headers["content-type"].startswith("text/plain")
        assert (
            'gateway_chat_requests_total{api="openai",backend="native",outcome="ok"} 1.0'
            in metrics.text
        )
        assert 'route="/v1/chat/completions"' in metrics.text

    def test_unknown_route_and_method(self, client: TestClient) -> None:
        assert client.get("/nope").json()["error"]["type"] == "not_found_error"
        assert client.get("/v1/chat/completions").status_code == 405


class TestConfiguration:
    def test_refuses_to_start_without_keys(self) -> None:
        with pytest.raises(ConfigurationError, match="ONE_MIN_API_KEY"):
            build_container(make_settings(one_min_api_key=""))
        with pytest.raises(ConfigurationError, match="gateway API key"):
            build_container(make_settings(gateway_api_keys=""))
        with pytest.raises(ConfigurationError, match="SHA-256"):
            build_container(make_settings(gateway_api_keys="agent:plain-text-key"))
        with pytest.raises(ConfigurationError, match="MODEL_ALIASES"):
            build_container(make_settings(model_aliases="broken"))


class TestMcp:
    def test_requires_a_gateway_key(self, client: TestClient) -> None:
        response = client.post("/mcp", headers=MCP_HEADERS, json=INITIALIZE)
        assert response.status_code == 401

    def test_initialize_and_list_tools_over_http(self, client: TestClient) -> None:
        headers = {**MCP_HEADERS, "Authorization": f"Bearer {CLIENT_KEY}"}
        response = client.post("/mcp", headers=headers, json=INITIALIZE)
        assert response.status_code == 200, response.text
        assert response.json()["result"]["serverInfo"]["name"] == "1min-gateway"
        listed = client.post(
            "/mcp",
            headers={**headers, "mcp-protocol-version": "2025-06-18"},
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert listed.status_code == 200, listed.text
        names = {tool["name"] for tool in listed.json()["result"]["tools"]}
        assert {
            "generate_image",
            "run_feature",
            "web_search",
            "analyze_image",
            "transcribe_audio",
        } <= names

    async def test_tools_call_the_services(
        self, container_factory: Callable[..., Any], fake: FakeOneMin
    ) -> None:
        container = container_factory()
        server = build_mcp_server(container)
        try:
            result = await server.call_tool("web_search", {"query": "news"})
            assert "Bonjour depuis 1min" in str(result)
            assert fake.last_json("/api/chat-with-ai")["promptObject"]["settings"][
                "webSearchSettings"
            ]["webSearch"]

            image = await server.call_tool("generate_image", {"prompt": "a cat"})
            assert "development/images/out-1.png" in str(image)

            translated = await server.call_tool(
                "translate_text", {"text": "hello", "target_language": "fr"}
            )
            assert "CONTENT_TRANSLATOR output" in str(translated)

            upload = await server.call_tool(
                "upload_file", {"filename": "a.txt", "content_base64": "aGVsbG8="}
            )
            assert "development/uploads" in str(upload)
        finally:
            await container.aclose()

    async def test_tool_errors_are_reported_not_leaked(
        self, container_factory: Callable[..., Any], fake: FakeOneMin
    ) -> None:
        container = container_factory()
        server = build_mcp_server(container)
        fake.overrides["/api/chat-with-ai"] = httpx.Response(
            429, json={"success": False, "error": {"code": "RATE_LIMITED", "message": "too many"}}
        )
        try:
            with pytest.raises(Exception, match="too many"):
                await server.call_tool("web_search", {"query": "news"})
            with pytest.raises(Exception, match="base64"):
                await server.call_tool("upload_file", {"filename": "a", "content_base64": "%%%"})
        finally:
            await container.aclose()
