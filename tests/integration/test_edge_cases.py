import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from gateway.interfaces.mcp.server import build_mcp_server
from tests.fakes import FakeOneMin, feature_record, native_chunk, sse


def _stream_text(response: Any) -> str:
    return response.read().decode()


def test_legacy_stream_refusal_is_a_regular_http_error(
    client: TestClient, fake: FakeOneMin, auth: dict[str, str]
) -> None:
    # Real 1min.ai behaviour: an `error` event whose data is a plain string.
    fake.legacy_stream = sse(
        ("error", {"error": "Model gemini-2.5-pro is not supported for feature UNIFY_CHAT_WITH_AI"})
    )
    response = client.post(
        "/v1/chat/completions",
        headers=auth,
        json={
            "model": "gemini-2.5-pro",
            "stream": True,
            "messages": [{"role": "user", "content": "x"}],
        },
    )
    assert response.status_code == 400
    assert "not supported" in response.json()["error"]["message"]


def test_claude_short_names_resolve_to_catalog_ids(
    client: TestClient, fake: FakeOneMin, auth: dict[str, str]
) -> None:
    client.post(
        "/v1/messages",
        headers={**auth, "anthropic-version": "2023-06-01"},
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 20,
            "messages": [{"role": "user", "content": "x"}],
        },
    )
    assert (
        fake.last_json("/api/chat-with-ai")["model"]
        == "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )


def test_image_sent_to_a_text_only_model(client: TestClient, auth: dict[str, str]) -> None:
    content = [
        {"type": "text", "text": "?"},
        {"type": "image_url", "image_url": {"url": "https://x/y.png"}},
    ]
    response = client.post(
        "/v1/chat/completions",
        headers=auth,
        json={"model": "sonar", "messages": [{"role": "user", "content": content}]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "model_not_vision_capable"


def test_feature_models_from_the_live_catalog(
    client: TestClient, fake: FakeOneMin, auth: dict[str, str]
) -> None:
    data = client.get("/v1/features/grammar_checker/models", headers=auth).json()["data"]
    assert {"gpt-5", "sonar"} <= {model["id"] for model in data}
    assert fake.calls("/models")[-1].url.params["feature"] == "GRAMMAR_CHECKER"
    assert client.get("/v1/features/bad type/models", headers=auth).status_code == 400


def test_legacy_stream_with_only_a_final_record(
    client: TestClient, fake: FakeOneMin, auth: dict[str, str]
) -> None:
    fake.legacy_stream = sse(
        (
            "result",
            {
                "aiRecord": {
                    "status": "SUCCESS",
                    "aiRecordDetail": {"resultObject": ["Full answer"]},
                }
            },
        ),
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
        assert "Full answer" in _stream_text(response)


def test_legacy_stream_with_tools_is_buffered_then_parsed(
    client: TestClient, fake: FakeOneMin, auth: dict[str, str]
) -> None:
    fake.legacy_stream = sse(
        ("content", {"content": '<tool_call>{"name": "f", '}),
        ("content", {"content": '"arguments": {"q": 1}}</tool_call>'}),
        ("done", {"message": "Stream completed"}),
    )
    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers=auth,
        json={
            "model": "claude-sonnet-4-5-20250929",
            "messages": [{"role": "user", "content": "x"}],
            "tools": [{"type": "function", "function": {"name": "f"}}],
            "stream": True,
        },
    ) as response:
        text = _stream_text(response)
    assert '"name":"f"' in text and '"finish_reason":"tool_calls"' in text


def test_native_stream_without_done_is_reported(
    client: TestClient, fake: FakeOneMin, auth: dict[str, str]
) -> None:
    fake.native_stream = sse((None, native_chunk({"content": "cut"})))
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
        text = _stream_text(response)
    assert "incomplete_stream" in text and "[DONE]" not in text


def test_error_before_streaming_is_a_regular_http_error(
    client: TestClient, fake: FakeOneMin, auth: dict[str, str]
) -> None:
    fake.overrides["/openai/v1/chat/completions"] = httpx.Response(
        400, json={"error": {"message": "temperature unsupported", "param": "temperature"}}
    )
    response = client.post(
        "/v1/chat/completions",
        headers=auth,
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "x"}],
            "stream": True,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["param"] == "temperature"


def test_unknown_native_catalog_routes_optimistically(
    client: TestClient, fake: FakeOneMin, auth: dict[str, str]
) -> None:
    fake.overrides["/openai/v1/models"] = httpx.Response(401, json={"error": {"message": "x"}})
    response = client.post(
        "/v1/chat/completions",
        headers=auth,
        json={"model": "brand-new-model", "messages": [{"role": "user", "content": "x"}]},
    )
    assert response.status_code == 200
    assert fake.last_json("/openai/v1/chat/completions")["model"] == "brand-new-model"
    models = client.get("/v1/models", headers=auth).json()["data"]
    assert all(model["backend"] == "legacy" for model in models)


def test_jobs_still_processing(
    client_factory: Callable[..., TestClient], fake: FakeOneMin, auth: dict[str, str]
) -> None:
    client = client_factory(feature_timeout_s=0.05)

    def never_done(body: dict[str, Any]) -> dict[str, Any]:
        record = feature_record("rec-slow", body["type"], body["model"], "PROCESSING", [])
        fake.pending["rec-slow"] = record
        return record

    fake.feature_handler = never_done
    image = client.post("/v1/images/generations", headers=auth, json={"prompt": "x"})
    assert image.status_code == 504
    assert image.json()["error"]["code"] == "feature_still_processing"
    fake.pending["rec-slow"] = feature_record(
        "rec-slow", "TEXT_TO_VIDEO", "kling", "PROCESSING", []
    )
    job = client.post(
        "/v1/features/TEXT_TO_VIDEO",
        headers=auth,
        json={"model": "kling", "timeout_s": 1, "prompt_object": {"prompt": "x"}},
    )
    assert job.status_code == 202 and job.json()["status"] == "processing"


def test_feature_request_validation(client: TestClient, auth: dict[str, str]) -> None:
    assert (
        client.post(
            "/v1/features/X Y", headers=auth, json={"model": "m", "prompt_object": {}}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/v1/features/SUMMARIZER", headers=auth, json={"mode": "later", "prompt_object": {}}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/v1/features/SUMMARIZER", headers=auth, json={"timeout_s": 0, "prompt_object": {}}
        ).status_code
        == 400
    )
    assert (
        client.post("/v1/features/SUMMARIZER", headers=auth, json={"model": "gpt-4o"}).status_code
        == 400
    )


def test_model_list_is_cached(client: TestClient, fake: FakeOneMin, auth: dict[str, str]) -> None:
    for _ in range(3):
        client.get("/v1/models", headers=auth)
    assert len(fake.calls("/openai/v1/models")) == 1


class TestMcpTools:
    @pytest.fixture
    def server_and_container(self, container_factory: Callable[..., Any]) -> Any:
        container = container_factory()
        return build_mcp_server(container), container

    async def test_media_and_feature_tools(
        self, server_and_container: Any, fake: FakeOneMin
    ) -> None:
        server, container = server_and_container
        try:
            speech = await server.call_tool("text_to_speech", {"text": "salut", "voice": "nova"})
            assert "speech.mp3" in str(speech)
            transcript = await server.call_tool(
                "transcribe_audio", {"asset_key": "audios/a.mp3", "language": "fr"}
            )
            assert "transcribed text" in str(transcript)
            vision = await server.call_tool(
                "analyze_image", {"image": "https://example.com/a.png", "question": "What?"}
            )
            assert "Bonjour depuis 1min" in str(vision)
            assert fake.last_json("/api/chat-with-ai")["promptObject"]["attachments"]["images"] == [
                "https://example.com/a.png"
            ]
            summary = await server.call_tool("summarize_youtube", {"url": "https://youtu.be/x"})
            assert "YOUTUBE_SUMMARIZER output" in str(summary)
            assert fake.last_json("/api/features")["videoUrl"] == "https://youtu.be/x"

            listed = await server.call_tool("list_features", {"category": "video"})
            assert "TEXT_TO_VIDEO" in str(listed) and "IMAGE_GENERATOR" not in str(listed)

            started = await server.call_tool(
                "run_feature",
                {"feature_type": "TEXT_TO_VIDEO", "prompt_object": {"prompt": "x"}, "wait": False},
            )
            record_id = json.loads(started.content[0].text)["id"]
            finished = await server.call_tool("get_feature_result", {"record_id": record_id})
            assert "succeeded" in str(finished)
            waited = await server.call_tool(
                "run_feature", {"feature_type": "SUMMARIZER", "prompt_object": {"prompt": "x"}}
            )
            assert "SUMMARIZER output" in str(waited)
        finally:
            await container.aclose()

    async def test_tool_failures(self, server_and_container: Any, fake: FakeOneMin) -> None:
        server, container = server_and_container

        def failing(body: dict[str, Any]) -> dict[str, Any]:
            return feature_record(
                "rec-f", body["type"], body["model"], "FAILED", {"message": "blocked"}
            )

        try:
            with pytest.raises(Exception, match="model is required"):
                await server.call_tool(
                    "run_feature", {"feature_type": "UNKNOWN_FEATURE", "prompt_object": {}}
                )
            fake.feature_handler = failing
            with pytest.raises(Exception, match="blocked"):
                await server.call_tool("translate_text", {"text": "x", "target_language": "fr"})
        finally:
            await container.aclose()
