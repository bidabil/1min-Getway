import json

from fastapi.testclient import TestClient

from tests.conftest import CLIENT_KEY
from tests.fakes import FakeOneMin, native_chunk, sse

HEADERS = {"x-api-key": CLIENT_KEY, "anthropic-version": "2023-06-01"}


def _sse_events(text: str) -> list[tuple[str, dict]]:  # type: ignore[type-arg]
    events: list[tuple[str, dict]] = []  # type: ignore[type-arg]
    name = ""
    for line in text.splitlines():
        if line.startswith("event: "):
            name = line[7:]
        elif line.startswith("data: "):
            events.append((name, json.loads(line[6:])))
    return events


def test_message_with_tool_round_trip(client: TestClient, fake: FakeOneMin) -> None:
    fake.native_reply = {
        "id": "chatcmpl-abc",
        "created": 1,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": "Let me check.",
                    "tool_calls": [
                        {
                            "id": "toolu_2",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": '{"city":"Rome"}'},
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 5},
    }
    response = client.post(
        "/v1/messages",
        headers=HEADERS,
        json={
            "model": "gpt-4o-mini",
            "max_tokens": 1024,
            "system": [{"type": "text", "text": "Be concise."}],
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Weather",
                    "input_schema": {"type": "object"},
                }
            ],
            "tool_choice": {"type": "any", "disable_parallel_tool_use": True},
            "messages": [
                {"role": "user", "content": "Weather in Paris and Rome?"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "get_weather",
                            "input": {"city": "Paris"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "12C"},
                        {"type": "text", "text": "And Rome?"},
                    ],
                },
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "message" and body["id"].startswith("msg_")
    assert body["model"] == "gpt-4o-mini"
    assert body["stop_reason"] == "tool_use"
    assert body["content"] == [
        {"type": "text", "text": "Let me check."},
        {"type": "tool_use", "id": "toolu_2", "name": "get_weather", "input": {"city": "Rome"}},
    ]
    assert body["usage"] == {"input_tokens": 20, "output_tokens": 5}

    upstream = fake.last_json("/openai/v1/chat/completions")
    roles = [message["role"] for message in upstream["messages"]]
    assert roles == ["system", "user", "assistant", "tool", "user"]
    assert upstream["messages"][3] == {"role": "tool", "tool_call_id": "toolu_1", "content": "12C"}
    assert upstream["tool_choice"] == "required"
    assert upstream["parallel_tool_calls"] is False
    assert upstream["max_completion_tokens"] == 1024


def test_streaming_event_sequence(client: TestClient, fake: FakeOneMin) -> None:
    fake.native_stream = sse(
        (None, native_chunk({"role": "assistant", "content": ""})),
        (None, native_chunk({"content": "Hi"})),
        (
            None,
            native_chunk(
                {
                    "tool_calls": [
                        {"index": 0, "id": "call_1", "function": {"name": "f", "arguments": '{"x"'}}
                    ]
                }
            ),
        ),
        (None, native_chunk({"tool_calls": [{"index": 0, "function": {"arguments": ":1}"}}]})),
        (None, native_chunk({}, "tool_calls")),
        (None, native_chunk(with_choice=False, usage={"prompt_tokens": 4, "completion_tokens": 2})),
        (None, "[DONE]"),
    )
    with client.stream(
        "POST",
        "/v1/messages",
        headers=HEADERS,
        json={
            "model": "gpt-4o-mini",
            "max_tokens": 50,
            "stream": True,
            "messages": [{"role": "user", "content": "x"}],
            "tools": [{"name": "f", "input_schema": {"type": "object"}}],
        },
    ) as response:
        events = _sse_events(response.read().decode())
    names = [name for name, _ in events]
    assert names == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    assert events[2][1]["delta"] == {"type": "text_delta", "text": "Hi"}
    assert events[4][1]["content_block"] == {
        "type": "tool_use",
        "id": "call_1",
        "name": "f",
        "input": {},
    }
    assert events[5][1]["delta"] == {"type": "input_json_delta", "partial_json": '{"x":1}'}
    assert events[7][1]["delta"]["stop_reason"] == "tool_use"
    assert events[7][1]["usage"] == {"input_tokens": 4, "output_tokens": 2}


def test_images_documents_and_web_search_use_legacy_api(
    client: TestClient, fake: FakeOneMin
) -> None:
    response = client.post(
        "/v1/messages",
        headers=HEADERS,
        json={
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 100,
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "iVBORw0KGgo=",
                            },
                        },
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": "JVBERi0x",
                            },
                            "title": "spec.pdf",
                        },
                        {"type": "text", "text": "Summarize"},
                    ],
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["content"][0]["text"] == "Bonjour depuis 1min"
    upstream = fake.last_json("/api/chat-with-ai")["promptObject"]
    assert upstream["attachments"] == {
        "images": ["development/uploads/asset-1"],
        "files": ["file-asset-2"],
    }
    assert upstream["settings"]["webSearchSettings"]["webSearch"] is True
    assert upstream["prompt"] == "[image 1]\n[file spec.pdf]\nSummarize"


def test_errors_use_anthropic_format(client: TestClient) -> None:
    response = client.post("/v1/messages", headers={"anthropic-version": "2023-06-01"}, json={})
    assert response.status_code == 401
    assert response.json() == {
        "type": "error",
        "error": {"type": "authentication_error", "message": response.json()["error"]["message"]},
    }
    response = client.post(
        "/v1/messages",
        headers=HEADERS,
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["type"] == "invalid_request_error"


def test_count_tokens_and_models(client: TestClient) -> None:
    response = client.post(
        "/v1/messages/count_tokens",
        headers=HEADERS,
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x" * 400}]},
    )
    assert response.json() == {"input_tokens": 100}
    models = client.get("/v1/models", headers=HEADERS).json()
    assert models["data"][0]["type"] == "model"
    assert {"has_more", "first_id", "last_id"} <= models.keys()
