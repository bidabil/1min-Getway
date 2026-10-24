import base64
import json
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from gateway.interfaces.http.app import create_app
from tests.fakes import PNG_BYTES, STORAGE, FakeOneMin, feature_record


class TestModels:
    def test_union_of_native_legacy_and_aliases(
        self, client_factory: Callable[..., TestClient], auth: dict[str, str]
    ) -> None:
        client = client_factory(
            model_aliases="my-agent-model=gpt-5,claude-*=gpt-5", legacy_chat_models="extra-model"
        )
        data = client.get("/v1/models", headers=auth).json()["data"]
        by_id = {model["id"]: model for model in data}
        assert (by_id["gpt-5"]["backend"], by_id["gpt-5"]["vision"]) == ("native", True)
        assert by_id["deepseek-chat"]["vision"] is False  # native only: no image path
        claude = by_id["us.anthropic.claude-sonnet-4-5-20250929-v1:0"]
        assert (claude["backend"], claude["vision"], claude["max_output_tokens"]) == (
            "legacy",
            True,
            64000,
        )
        assert by_id["sonar"]["vision"] is False
        assert "retired-model" not in by_id  # DISABLED in the catalog
        assert by_id["extra-model"]["backend"] == "legacy"
        assert by_id["my-agent-model"]["alias_of"] == "gpt-5"
        assert "claude-*" not in by_id
        assert [m["id"] for m in data].count("gpt-5") == 1
        assert client.get("/v1/models/gpt-5", headers=auth).json()["id"] == "gpt-5"
        assert client.get("/v1/models/nope", headers=auth).status_code == 404

    def test_alias_routes_to_target(
        self, client_factory: Callable[..., TestClient], fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        client = client_factory(model_aliases="claude-*=gpt-5")
        client.post(
            "/v1/chat/completions",
            headers=auth,
            json={"model": "claude-opus-4-5", "messages": [{"role": "user", "content": "x"}]},
        )
        assert fake.last_json("/openai/v1/chat/completions")["model"] == "gpt-5"


class TestFeatures:
    def test_catalog(self, client: TestClient, auth: dict[str, str]) -> None:
        data = client.get("/v1/features", headers=auth).json()["data"]
        assert any(spec["type"] == "TEXT_TO_VIDEO" and spec["long_running"] for spec in data)
        spec = client.get("/v1/features/content_translator", headers=auth).json()
        assert {field["name"] for field in spec["fields"]} >= {"targetLanguage", "prompt"}
        assert client.get("/v1/features/NOPE", headers=auth).status_code == 404

    def test_wait_mode_polls_until_done(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/features/content_translator",
            headers=auth,
            json={"prompt_object": {"prompt": "Hello", "targetLanguage": "fr"}},
        )
        assert response.status_code == 200
        body = response.json()
        assert (body["status"], body["results"], body["model"]) == (
            "succeeded",
            ["CONTENT_TRANSLATOR output"],
            "gpt-4o",
        )
        upstream = fake.last_json("/api/features")
        assert upstream["async"] is True
        assert upstream["conversationId"] == "CONTENT_TRANSLATOR"
        assert len(fake.calls(f"/api/results/{body['id']}")) == 1

    def test_async_mode_then_result_endpoint(
        self, client: TestClient, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/features/TEXT_TO_VIDEO",
            headers=auth,
            json={
                "model": "kling",
                "mode": "async",
                "prompt_object": {"prompt": "a cat", "duration": 5, "version": "1.6"},
            },
        )
        assert response.status_code == 202
        record_id = response.json()["id"]
        result = client.get(f"/v1/features/results/{record_id}", headers=auth)
        assert result.status_code == 200 and result.json()["status"] == "succeeded"
        assert client.get("/v1/features/results/unknown-id", headers=auth).status_code == 404
        assert client.get("/v1/features/results/bad%20id", headers=auth).status_code == 400

    def test_any_documented_type_and_extra_fields(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/features/keyword_research",
            headers=auth,
            json={
                "model": "gpt-4o",
                "mode": "sync",
                "prompt_object": {"prompt": "seo"},
                "extra": {"brandVoiceId": "bv1"},
            },
        )
        assert response.status_code == 200
        upstream = fake.last_json("/api/features")
        assert upstream == {
            "brandVoiceId": "bv1",
            "type": "KEYWORD_RESEARCH",
            "model": "gpt-4o",
            "promptObject": {"prompt": "seo"},
        }
        missing_model = client.post(
            "/v1/features/keyword_research", headers=auth, json={"prompt_object": {}}
        )
        assert missing_model.status_code == 400

    def test_failed_feature(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        def failing(body: dict[str, Any]) -> dict[str, Any]:
            return feature_record(
                "rec-x", body["type"], body["model"], "FAILURE", {"message": "moderation"}
            )

        fake.feature_handler = failing
        response = client.post("/v1/images/generations", headers=auth, json={"prompt": "x"})
        assert response.status_code == 502
        assert "moderation" in response.json()["error"]["message"]


class TestImages:
    def test_generation_maps_size_and_returns_urls(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/images/generations",
            headers=auth,
            json={
                "prompt": "a lighthouse",
                "model": "black-forest-labs/flux-schnell",
                "size": "1024x1792",
                "prompt_object": {"seed": 42},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == [
            {"asset_key": "development/images/out-1.png", "url": f"{STORAGE}/result.png"}
        ]
        upstream = fake.last_json("/api/features")
        assert upstream["promptObject"] == {
            "prompt": "a lighthouse",
            "aspect_ratio": "9:16",
            "seed": 42,
        }

    def test_base64_output_downloads_without_leaking_the_key(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/images/generations",
            headers=auth,
            json={"prompt": "x", "response_format": "b64_json"},
        )
        assert base64.b64decode(response.json()["data"][0]["b64_json"]) == PNG_BYTES
        download = next(
            request for request in fake.requests if request.url.host == "storage.example"
        )
        assert "api-key" not in download.headers and "authorization" not in download.headers

    def test_edit_uploads_the_image(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/images/edits",
            headers=auth,
            files={"image": ("in.png", PNG_BYTES, "image/png")},
            data={"prompt": "add a hat", "quality": "high"},
        )
        assert response.status_code == 200
        upstream = fake.last_json("/api/features")
        assert upstream["type"] == "IMAGE_EDITOR"
        assert upstream["promptObject"]["imageUrl"] == "development/uploads/asset-1"
        assert upstream["promptObject"]["quality"] == "high"

    def test_variation(self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]) -> None:
        response = client.post(
            "/v1/images/variations",
            headers=auth,
            files={"image": ("in.png", PNG_BYTES, "image/png")},
            data={"n": "4"},
        )
        assert response.status_code == 200
        assert fake.last_json("/api/features")["promptObject"] == {
            "imageUrl": "development/uploads/asset-1",
            "n": 4,
        }


class TestAudioAndFiles:
    def test_speech_returns_audio_bytes(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        response = client.post(
            "/v1/audio/speech",
            headers=auth,
            json={"input": "Bonjour", "voice": "nova", "speed": 1.2},
        )
        assert response.status_code == 200
        assert response.content == b"ID3-fake-audio"
        assert response.headers["content-type"] == "audio/mpeg"
        assert fake.last_json("/api/features")["promptObject"] == {
            "text": "Bonjour",
            "voice": "nova",
            "response_format": "mp3",
            "speed": 1.2,
        }
        assert fake.last_json("/api/features")["conversationId"] == "TEXT_TO_SPEECH"

    def test_transcription_formats(
        self, client: TestClient, fake: FakeOneMin, auth: dict[str, str]
    ) -> None:
        files = {"file": ("a.mp3", b"ID3", "audio/mpeg")}
        response = client.post(
            "/v1/audio/transcriptions", headers=auth, files=files, data={"language": "fr"}
        )
        assert response.json() == {"text": "transcribed text"}
        assert fake.last_json("/api/features")["promptObject"] == {
            "audioUrl": "development/uploads/asset-1",
            "response_format": "text",
            "language": "fr",
        }
        text = client.post(
            "/v1/audio/transcriptions", headers=auth, files=files, data={"response_format": "text"}
        )
        assert text.text == "transcribed text"
        invalid = client.post(
            "/v1/audio/transcriptions", headers=auth, files=files, data={"response_format": "mp4"}
        )
        assert invalid.status_code == 400

    def test_file_upload(self, client: TestClient, auth: dict[str, str]) -> None:
        response = client.post(
            "/v1/files",
            headers=auth,
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
            data={"purpose": "assistants"},
        )
        body = response.json()
        assert body["object"] == "file" and body["id"] == "development/uploads/asset-1"
        assert body["file_id"] == "file-asset-1" and body["purpose"] == "assistants"
        empty = client.post("/v1/files", headers=auth, files={"file": ("e.txt", b"", "text/plain")})
        assert empty.status_code == 400


def test_errors_do_not_leak_internals(
    container_factory: Callable[..., Any], fake: FakeOneMin, auth: dict[str, str]
) -> None:
    def explode(body: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("secret internal detail")

    fake.feature_handler = explode
    with TestClient(
        create_app(container=container_factory()), raise_server_exceptions=False
    ) as client:
        response = client.post(
            "/v1/features/SUMMARIZER", headers=auth, json={"prompt_object": {"prompt": "x"}}
        )
    assert response.status_code == 500
    assert response.json()["error"]["message"] == "Internal gateway error."
    assert "secret internal detail" not in json.dumps(response.json())
