import json
from collections.abc import Callable

import httpx
from fastapi.testclient import TestClient

from tests.conftest import CLIENT_KEY, OTHER_KEY
from tests.fakes import FakeOneMin, native_chunk, sse


def _events(text: str) -> list[dict | str]:  # type: ignore[type-arg]
    payloads: list[dict | str] = []  # type: ignore[type-arg]
    for line in text.splitlines():
        if line.startswith("data: "):
            data = line[6:]
            payloads.append(data if data == "[DONE]" else json.loads(data))
    return payloads


class TestAuthentication:
    def test_missing_and_invalid_keys(self, client: TestClient) -> None:
        response = client.post("/v1/chat/completions", json={})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "missing_api_key"
        assert response.headers["WWW-Authenticate"] == "Bearer"
        response = client.post(
            "/v1/chat/completions", json={}, headers={"Authorization": "Bearer nope"}
        )
        assert response.json()["error"] == {
            "message": "Invalid API key.",
            "type": "authentication_error",
            "param": None,
            "code": "invalid_api_key",
        }

    def test_alternative_headers(self, client: TestClient) -> None:
        body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]}
        assert (
            client.post(
                "/v1/chat/completions", json=body, headers={"x-api-key": CLIENT_KEY}
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/v1/chat/completions", json=body, headers={"Authorization": f"bearer {CLIENT_KEY}"}
            ).status_code
            == 200
        )

    def test_per_key_rate_limit(self, client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {OTHER_KEY}"}  # configured at 2 requests/minute
        assert client.get("/v1/models", headers=headers).status_code == 200
        assert client.get("/v1/models", headers=headers).status_code == 200
        limited = client.get("/v1/models", headers=headers)
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) >= 1
        assert limited.json()["error"]["type"] == "rate_limit_error"


class TestNativeChat:
    def test_completion_and_upstream_payload(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "gpt-5",
                "messages": [
                    {"role": "system", "content": "Be brief"},
                    {"role": "user", "content": "Hi"},
                ],
                "temperature": 0.7,
                "max_tokens": 99_999,
                "user": "u-1",
                "logprobs": False,
                "tools": [
                    {
                        "type": "function",
                        "function": {"name": "f", "parameters": {"type": "object"}},
                    }
                ],
                "tool_choice": "auto",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["object"] == "chat.completion"
        assert body["choices"][0]["message"]["content"] == "Hello from native"
        assert body["usage"] == {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}
        assert response.headers["X-Request-ID"]

        upstream = fake.last_json("/openai/v1/chat/completions")
        assert upstream["model"] == "gpt-5"
        assert upstream["max_completion_tokens"] == 32768  # capped
        assert "temperature" not in upstream  # dropped for reasoning models
        assert "user" not in upstream and "logprobs" not in upstream  # unknown fields not forwarded
        assert upstream["tools"][0]["function"]["name"] == "f"
        assert upstream["messages"][0] == {"role": "system", "content": "Be brief"}

    def test_tool_calls_are_returned(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        fake.native_reply = {
            "id": "chatcmpl-x",
            "created": 1,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "f", "arguments": '{"a":1}'},
                            }
                        ],
                    },
                }
            ],
        }
        response = client.post(
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "x"}],
                "tools": [{"type": "function", "function": {"name": "f"}}],
            },
        )
        choice = response.json()["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        assert choice["message"]["tool_calls"][0]["function"] == {
            "name": "f",
            "arguments": '{"a":1}',
        }

    def test_history_with_tool_results_is_forwarded(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        messages = [
            {"role": "user", "content": "weather?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "w", "arguments": {"city": "Paris"}},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "12C"},
        ]
        client.post(
            "/v1/chat/completions",
            headers=auth,
            json={"model": "gpt-4o-mini", "messages": messages},
        )
        upstream = fake.last_json("/openai/v1/chat/completions")["messages"]
        assert upstream[1]["tool_calls"][0]["function"]["arguments"] == '{"city": "Paris"}'
        assert upstream[2] == {"role": "tool", "tool_call_id": "call_1", "content": "12C"}

    def test_stream_keeps_newlines_and_reports_usage(
        self, client: TestClient, auth: dict[str, str]
    ) -> None:
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
                "stream_options": {"include_usage": True},
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            events = _events(response.read().decode())
        assert events[-1] == "[DONE]"
        text = "".join(
            e["choices"][0]["delta"].get("content", "")
            for e in events
            if isinstance(e, dict) and e["choices"]
        )
        assert text == "Hello\n\nWorld"
        assert events[0]["choices"][0]["delta"]["role"] == "assistant"  # type: ignore[index]
        assert events[-2]["usage"]["total_tokens"] == 10  # type: ignore[index]

    def test_stream_without_usage_option(self, client: TestClient, auth: dict[str, str]) -> None:
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        ) as response:
            events = _events(response.read().decode())
        assert not any(isinstance(e, dict) and "usage" in e for e in events)

    def test_stream_streams_tool_call_fragments(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        fake.native_stream = sse(
            (
                None,
                native_chunk(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "f", "arguments": ""},
                            }
                        ],
                    }
                ),
            ),
            (
                None,
                native_chunk({"tool_calls": [{"index": 0, "function": {"arguments": '{"a":'}}]}),
            ),
            (None, native_chunk({"tool_calls": [{"index": 0, "function": {"arguments": "1}"}}]})),
            (None, native_chunk({}, "tool_calls")),
            (None, "[DONE]"),
        )
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            events = [e for e in _events(response.read().decode()) if isinstance(e, dict)]
        fragments = [
            c["function"]["arguments"]
            for e in events
            for c in e["choices"][0]["delta"].get("tool_calls", [])
        ]
        assert "".join(fragments) == '{"a":1}'
        assert events[-1]["choices"][0]["finish_reason"] == "tool_calls"

    def test_upstream_error_frame_mid_stream(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        fake.native_stream = sse(
            (None, native_chunk({"content": "partial"})),
            (None, {"error": {"message": "deadline exceeded", "code": "timeout"}}),
        )
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            events = _events(response.read().decode())
        assert events[-1]["error"]["message"] == "deadline exceeded"  # type: ignore[index]
        assert "[DONE]" not in events

    def test_upstream_errors_map_to_clear_statuses(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]}
        fake.overrides["/openai/v1/chat/completions"] = httpx.Response(
            429, json={"error": {"message": "slow"}}, headers={"retry-after": "3"}
        )
        response = client.post("/v1/chat/completions", headers=auth, json=body)
        assert (response.status_code, response.headers["Retry-After"]) == (429, "3")
        fake.overrides["/openai/v1/chat/completions"] = httpx.Response(503, text="down")
        assert client.post("/v1/chat/completions", headers=auth, json=body).status_code == 502
        fake.overrides["/openai/v1/chat/completions"] = httpx.Response(
            401, json={"error": {"message": "x"}}
        )
        response = client.post("/v1/chat/completions", headers=auth, json=body)
        assert (response.status_code, response.json()["error"]["code"]) == (
            502,
            "upstream_authentication_failed",
        )


class TestLegacyChat:
    def test_claude_is_served_by_chat_with_ai_with_full_history(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "claude-sonnet-4-5-20250929",
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "My name is Ada."},
                    {"role": "assistant", "content": "Hello Ada!"},
                    {"role": "user", "content": "What is my name?"},
                ],
            },
        )
        assert response.status_code == 200
        assert response.json()["choices"][0]["message"]["content"] == "Bonjour depuis 1min"
        assert response.json()["usage"]["prompt_tokens"] > 0
        upstream = fake.last_json("/api/chat-with-ai")
        assert upstream["type"] == "UNIFY_CHAT_WITH_AI"
        assert "conversationId" not in upstream["promptObject"]
        prompt = upstream["promptObject"]["prompt"]
        assert (
            "You are helpful." in prompt and "My name is Ada." in prompt and "Hello Ada!" in prompt
        )

    def test_emulated_tool_calls(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        fake.legacy_text = (
            'Sure.<tool_call>{"name": "get_weather", "arguments": {"city": "Paris"}}</tool_call>'
        )
        response = client.post(
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "claude-sonnet-4-5-20250929",
                "messages": [{"role": "user", "content": "Weather in Paris?"}],
                "tools": [
                    {
                        "type": "function",
                        "function": {"name": "get_weather", "parameters": {"type": "object"}},
                    }
                ],
            },
        )
        choice = response.json()["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        assert choice["message"]["content"] == "Sure."
        assert json.loads(choice["message"]["tool_calls"][0]["function"]["arguments"]) == {
            "city": "Paris"
        }
        assert "<tool_call>" in fake.last_json("/api/chat-with-ai")["promptObject"]["prompt"]

    def test_protocol_text_is_not_parsed_without_tools(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        fake.legacy_text = '<tool_call>{"name": "delete_all", "arguments": {}}</tool_call>'
        response = client.post(
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "claude-sonnet-4-5-20250929",
                "messages": [{"role": "user", "content": "echo"}],
            },
        )
        message = response.json()["choices"][0]["message"]
        assert message["content"] == fake.legacy_text
        assert "tool_calls" not in message

    def test_vision_uploads_inline_images_and_passes_urls(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        content = [
            {"type": "text", "text": "Compare"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgo="}},
            {"type": "image_url", "image_url": {"url": "https://example.com/b.png"}},
        ]
        response = client.post(
            "/v1/chat/completions",
            headers=auth,
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": content}]},
        )
        assert response.status_code == 200
        assert len(fake.calls("/api/assets")) == 1
        upstream = fake.last_json("/api/chat-with-ai")["promptObject"]
        assert upstream["attachments"]["images"] == [
            "development/uploads/asset-1",
            "https://example.com/b.png",
        ]
        assert upstream["prompt"] == "Compare\n[image 1]\n[image 2]"
        assert not fake.calls("/openai/v1/chat/completions")

    def test_web_search_suffix(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        client.post(
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "gpt-4o-mini:online",
                "messages": [{"role": "user", "content": "news?"}],
            },
        )
        upstream = fake.last_json("/api/chat-with-ai")
        assert upstream["model"] == "gpt-4o-mini"
        assert upstream["promptObject"]["settings"]["webSearchSettings"] == {
            "webSearch": True,
            "numOfSite": 3,
            "maxWord": 1000,
        }

    def test_stream_preserves_formatting_and_tolerates_scalars(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        fake.legacy_stream = sse(
            ("content", {"content": "Year "}),
            ("content", "2024"),
            ("content", {"content": "\n\n- item"}),
            ("content", {"content": "\n\U0001f310 Crawling site https://x\n"}),
            ("done", {"message": "Stream completed"}),
        )
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "claude-sonnet-4-5-20250929",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            events = _events(response.read().decode())
        text = "".join(
            e["choices"][0]["delta"].get("content", "")
            for e in events
            if isinstance(e, dict) and e["choices"]
        )
        assert text == "Year 2024\n\n- item\n"
        assert events[-1] == "[DONE]"

    def test_legacy_streaming_error_event(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        fake.legacy_stream = sse(
            ("content", {"content": "a"}), ("error", {"error": {"message": "quota"}})
        )
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=auth,
            json={
                "model": "claude-sonnet-4-5-20250929",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            events = _events(response.read().decode())
        assert events[-1]["error"]["message"] == "quota"  # type: ignore[index]


class TestValidation:
    def test_request_errors(self, client: TestClient, auth: dict[str, str]) -> None:
        cases = [
            ({"model": "gpt-4o-mini"}, "messages"),
            (
                {"model": "gpt-4o-mini", "messages": [{"role": "robot", "content": "x"}]},
                "messages[0].role",
            ),
            ({"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}], "n": 2}, "n"),
            (
                {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": [{"type": "input_audio"}]}],
                },
                "messages[0].content[0].type",
            ),
            ({"model": "unknown-model", "messages": [{"role": "user", "content": "x"}]}, "model"),
        ]
        for body, param in cases:
            response = client.post("/v1/chat/completions", headers=auth, json=body)
            assert response.status_code in (400, 404), body
            assert response.json()["error"]["param"] == param

    def test_body_must_be_json_object(self, client: TestClient, auth: dict[str, str]) -> None:
        response = client.post(
            "/v1/chat/completions",
            headers={**auth, "content-type": "application/json"},
            content=b"[1]",
        )
        assert response.status_code == 400

    def test_body_size_limit(
        self, client_factory: Callable[..., TestClient], auth: dict[str, str]
    ) -> None:
        small = client_factory(max_request_body_mb=1)
        response = small.post(
            "/v1/chat/completions", headers=auth, content=b"x" * (2 * 1024 * 1024)
        )
        assert response.status_code == 413
