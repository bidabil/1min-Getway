"""In-memory fake of the 1min.ai HTTP APIs, plugged in through httpx.MockTransport."""

import json
from collections.abc import Callable
from typing import Any

import httpx

UPSTREAM_KEY = "sk-1min-test"
BASE_URL = "https://api.1min.test"
STORAGE = "https://storage.example"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def sse(*events: tuple[str | None, Any]) -> bytes:
    lines: list[str] = []
    for event, data in events:
        payload = data if isinstance(data, str) else json.dumps(data)
        if event:
            lines.append(f"event: {event}\n")
        lines.append(f"data: {payload}\n\n")
    return "".join(lines).encode()


def native_chunk(
    delta: dict[str, Any] | None = None,
    finish_reason: str | None = None,
    *,
    model: str = "gpt-4o-mini",
    usage: dict[str, Any] | None = None,
    with_choice: bool = True,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": "chatcmpl-upstream",
        "object": "chat.completion.chunk",
        "created": 1_700_000_000,
        "model": model,
        "choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish_reason}]
        if with_choice
        else [],
    }
    if usage is not None:
        body["usage"] = usage
    return body


def feature_record(
    record_id: str,
    feature_type: str,
    model: str,
    status: str,
    result: Any,
    temporary_url: str | None = None,
) -> dict[str, Any]:
    return {
        "uuid": record_id,
        "type": feature_type,
        "model": model,
        "status": status,
        "createdAt": "2026-10-22T00:00:00.000Z",
        "aiRecordDetail": {"promptObject": {}, "resultObject": result},
        "temporaryUrl": temporary_url,
    }


class FakeOneMin:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.native_models = ["gpt-4o-mini", "gpt-5", "deepseek-chat"]
        # Public catalog (GET /models?feature=...): (modelId, accepts images, status)
        self.catalog_models: list[tuple[str, bool, str]] = [
            ("us.anthropic.claude-sonnet-4-5-20250929-v1:0", True, "ACTIVE"),
            ("us.anthropic.claude-haiku-4-5-20251001-v1:0", True, "ACTIVE"),
            ("gemini-2.5-pro", True, "ACTIVE"),
            ("gpt-4o-mini", True, "ACTIVE"),
            ("gpt-5", True, "ACTIVE"),
            ("sonar", False, "ACTIVE"),
            ("retired-model", True, "DISABLED"),
        ]
        self.native_reply: dict[str, Any] | None = None
        self.native_stream: bytes | None = None
        self.legacy_text = "Bonjour depuis 1min"
        self.legacy_stream: bytes | None = None
        self.overrides: dict[str, httpx.Response] = {}
        self.feature_handler: Callable[[dict[str, Any]], dict[str, Any]] = self.default_feature
        self.pending: dict[str, dict[str, Any]] = {}
        self.storage: dict[str, tuple[bytes, str]] = {
            f"{STORAGE}/result.png": (PNG_BYTES, "image/png"),
            f"{STORAGE}/speech.mp3": (b"ID3-fake-audio", "audio/mpeg"),
        }
        self._counter = 0

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def calls(self, path: str) -> list[httpx.Request]:
        return [request for request in self.requests if request.url.path == path]

    def last_json(self, path: str) -> dict[str, Any]:
        calls = self.calls(path)
        assert calls, f"no call to {path}"
        payload: dict[str, Any] = json.loads(calls[-1].content)
        return payload

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter}"

    # --- request routing -------------------------------------------------------------

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host == "storage.example":
            item = self.storage.get(str(request.url).split("?")[0])
            if item is None:
                return httpx.Response(404)
            return httpx.Response(200, content=item[0], headers={"content-type": item[1]})

        path = request.url.path
        if path in self.overrides:
            return self.overrides[path]
        if path.startswith("/openai/"):
            if request.headers.get("authorization") != f"Bearer {UPSTREAM_KEY}":
                return httpx.Response(
                    401, json={"error": {"message": "bad key", "type": "invalid_request_error"}}
                )
        elif request.headers.get("api-key") != UPSTREAM_KEY:
            return httpx.Response(
                401,
                json={"success": False, "error": {"code": "UNAUTHORIZED", "message": "bad key"}},
            )

        if path == "/models":
            feature = request.url.params.get("feature", "")
            models = [
                {
                    "modelId": model_id,
                    "name": model_id.upper(),
                    "provider": "test",
                    "status": status,
                    "features": [feature, "GRAMMAR_CHECKER"],
                    "modality": {
                        "INPUT": ["text", "image"] if vision else ["text"],
                        "OUTPUT": ["text"],
                    },
                    "creditMetadata": {"MAX_OUTPUT_TOKEN": 64000},
                }
                for model_id, vision, status in self.catalog_models
            ]
            return httpx.Response(200, json={"models": models, "total": len(models)})
        if path == "/openai/v1/models":
            data = [
                {"id": model, "object": "model", "created": 1, "owned_by": "openai"}
                for model in self.native_models
            ]
            return httpx.Response(200, json={"object": "list", "data": data})
        if path == "/openai/v1/chat/completions":
            return self._native_chat(json.loads(request.content))
        if path == "/api/chat-with-ai":
            if request.url.params.get("isStreaming") == "true":
                return self._legacy_stream()
            return httpx.Response(
                200,
                json={
                    "aiRecord": feature_record(
                        "chat-1", "UNIFY_CHAT_WITH_AI", "x", "SUCCESS", [self.legacy_text]
                    )
                },
            )
        if path == "/api/assets":
            return self._asset(request)
        if path == "/api/features":
            return httpx.Response(
                200, json={"aiRecord": self.feature_handler(json.loads(request.content))}
            )
        if path.startswith("/api/results/"):
            record_id = path.rsplit("/", 1)[-1]
            # Like 1min.ai: the same record is returned on every poll; unknown ids give null.
            return httpx.Response(200, json={"aiRecord": self.pending.get(record_id)})
        return httpx.Response(
            404, json={"success": False, "error": {"code": "NOT_FOUND", "message": path}}
        )

    def _native_chat(self, body: dict[str, Any]) -> httpx.Response:
        if body.get("stream"):
            stream = self.native_stream or sse(
                (None, native_chunk({"role": "assistant", "content": ""}, model=body["model"])),
                (None, native_chunk({"content": "Hel"}, model=body["model"])),
                (None, native_chunk({"content": "lo\n\nWorld"}, model=body["model"])),
                (None, native_chunk({}, "stop", model=body["model"])),
                (
                    None,
                    native_chunk(
                        model=body["model"],
                        with_choice=False,
                        usage={"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
                    ),
                ),
                (None, "[DONE]"),
            )
            return httpx.Response(
                200, content=stream, headers={"content-type": "text/event-stream"}
            )
        reply = self.native_reply or {
            "id": "chatcmpl-upstream",
            "object": "chat.completion",
            "created": 1_700_000_000,
            "model": body["model"],
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello from native"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
        }
        return httpx.Response(200, json=reply)

    def _legacy_stream(self) -> httpx.Response:
        stream = self.legacy_stream or sse(
            ("content", {"content": "Bon"}),
            ("content", {"content": "jour\n\n- point"}),
            ("result", {"aiRecord": {"status": "SUCCESS"}}),
            ("done", {"message": "Stream completed"}),
        )
        return httpx.Response(200, content=stream, headers={"content-type": "text/event-stream"})

    def _asset(self, request: httpx.Request) -> httpx.Response:
        number = self._next_id("asset")
        content_type = request.headers.get("content-type", "")
        assert content_type.startswith("multipart/form-data"), content_type
        assert b'name="asset"' in request.content
        return httpx.Response(
            200,
            json={
                "asset": {
                    "key": f"development/uploads/{number}",
                    "originalname": "upload",
                    "size": len(request.content),
                    "mimetype": "application/octet-stream",
                },
                "fileContent": {
                    "uuid": f"file-{number}",
                    "path": f"uploads/{number}",
                    "createdAt": "2026-10-22T00:00:00Z",
                },
            },
        )

    def default_feature(self, body: dict[str, Any]) -> dict[str, Any]:
        feature_type, model = body["type"], body["model"]
        record_id = self._next_id("rec")
        temporary_url = None
        if feature_type in ("IMAGE_GENERATOR", "IMAGE_EDITOR", "IMAGE_VARIATOR"):
            result: Any = ["development/images/out-1.png"]
            temporary_url = f"{STORAGE}/result.png"
        elif feature_type == "TEXT_TO_SPEECH":
            result = ["development/audios/speech.mp3"]
            temporary_url = f"{STORAGE}/speech.mp3"
        elif feature_type == "SPEECH_TO_TEXT":
            result = ["transcribed text"]
        else:
            result = [f"{feature_type} output"]
        final = feature_record(record_id, feature_type, model, "SUCCESS", result, temporary_url)
        if body.get("async"):
            self.pending[record_id] = final
            return feature_record(record_id, feature_type, model, "PROCESSING", [])
        return final
