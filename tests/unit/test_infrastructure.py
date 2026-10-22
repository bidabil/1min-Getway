import httpx
import pytest

from gateway.domain.clients import ClientIdentity
from gateway.domain.errors import (
    ErrorKind,
    InvalidRequestError,
    RateLimitError,
    UpstreamError,
    UpstreamTimeoutError,
)
from gateway.domain.features import FeatureStatus
from gateway.infrastructure.one_min.catalog import StaticFeatureCatalog
from gateway.infrastructure.one_min.downloads import ResultDownloader
from gateway.infrastructure.one_min.errors import upstream_error
from gateway.infrastructure.one_min.features import parse_record
from gateway.infrastructure.one_min.legacy_chat import content_text, result_text
from gateway.infrastructure.one_min.sse import SSEEvent, iter_sse
from gateway.infrastructure.security.api_keys import (
    StaticApiKeyVerifier,
    generate_key,
    hash_key,
    parse_key_entries,
)
from gateway.infrastructure.security.rate_limit import TokenBucketLimiter


async def _lines(*lines: str):  # type: ignore[no-untyped-def]
    for line in lines:
        yield line


class TestSSE:
    async def test_preserves_whitespace_and_joins_multiline_data(self) -> None:
        events = [
            event
            async for event in iter_sse(
                _lines(
                    ": comment",
                    "event: content",
                    "data:  two spaces ",
                    "",
                    "data: a",
                    "data: b",
                    "",
                )
            )
        ]
        assert events == [SSEEvent("content", " two spaces "), SSEEvent("message", "a\nb")]

    async def test_flushes_trailing_event(self) -> None:
        events = [event async for event in iter_sse(_lines("data: [DONE]"))]
        assert events == [SSEEvent("message", "[DONE]")]


class TestLegacyParsing:
    def test_content_text_tolerates_every_shape(self) -> None:
        assert content_text('{"content": "\\n\\n- item"}') == "\n\n- item"
        assert content_text('"quoted"') == "quoted"
        assert content_text("2024") == "2024"  # a bare JSON scalar is text, not a crash
        assert content_text("raw text ") == "raw text "

    def test_result_text_and_failures(self) -> None:
        assert (
            result_text(
                {"aiRecord": {"status": "SUCCESS", "aiRecordDetail": {"resultObject": ["a", "b"]}}}
            )
            == "ab"
        )
        with pytest.raises(UpstreamError):
            result_text(
                {
                    "aiRecord": {
                        "status": "FAILED",
                        "aiRecordDetail": {"resultObject": {"message": "no"}},
                    }
                }
            )


class TestUpstreamErrors:
    @pytest.mark.parametrize(
        ("status", "body", "kind", "code"),
        [
            (
                400,
                {"error": {"message": "bad", "code": "x", "param": "messages"}},
                ErrorKind.INVALID_REQUEST,
                "x",
            ),
            (
                422,
                {
                    "success": False,
                    "error": {
                        "code": "PROMPT_OBJECT_VALIDATION_FAILED",
                        "message": "invalid",
                        "details": [{"field": "prompt", "message": "required"}],
                    },
                },
                ErrorKind.INVALID_REQUEST,
                "PROMPT_OBJECT_VALIDATION_FAILED",
            ),
            (
                401,
                {"error": {"message": "bad key"}},
                ErrorKind.UPSTREAM,
                "upstream_authentication_failed",
            ),
            (
                403,
                {"success": False, "error": {"code": "FORBIDDEN", "message": "no"}},
                ErrorKind.PERMISSION,
                "FORBIDDEN",
            ),
            (404, {"error": {"message": "model gone"}}, ErrorKind.NOT_FOUND, "not_found"),
            (
                429,
                {"error": {"message": "slow down"}},
                ErrorKind.RATE_LIMITED,
                "upstream_rate_limited",
            ),
            (
                429,
                {"error": {"message": "credits", "code": "insufficient_quota"}},
                ErrorKind.RATE_LIMITED,
                "insufficient_quota",
            ),
            (500, {"error": {"message": "boom"}}, ErrorKind.UPSTREAM, "upstream_error"),
            (503, "Service Unavailable", ErrorKind.UPSTREAM, "upstream_error"),
            (524, "", ErrorKind.UPSTREAM_TIMEOUT, "upstream_timeout"),
        ],
    )
    def test_mapping(self, status: int, body: object, kind: ErrorKind, code: str) -> None:
        response = (
            httpx.Response(status, json=body)
            if isinstance(body, dict)
            else httpx.Response(status, text=str(body))
        )
        error = upstream_error(response)
        assert (error.kind, error.code) == (kind, code)

    def test_validation_details_and_retry_after(self) -> None:
        error = upstream_error(
            httpx.Response(
                422,
                json={
                    "success": False,
                    "error": {
                        "message": "invalid",
                        "details": [{"field": "prompt", "message": "required"}],
                    },
                },
            )
        )
        assert error.message == "invalid (prompt: required)"
        limited = upstream_error(httpx.Response(429, headers={"retry-after": "7"}, json={}))
        assert isinstance(limited, RateLimitError) and limited.retry_after == 7.0


class TestFeatureRecords:
    def test_status_and_result_shapes(self) -> None:
        success = parse_record(
            {
                "uuid": "r1",
                "status": "SUCCESS",
                "aiRecordDetail": {"resultObject": ["k"]},
                "temporaryUrl": "https://s/x",
            },
            None,
        )
        assert (success.status, success.results, success.temporary_url) == (
            FeatureStatus.SUCCEEDED,
            ("k",),
            "https://s/x",
        )
        failure = parse_record(
            {
                "uuid": "r2",
                "status": "FAILURE",
                "aiRecordDetail": {"resultObject": {"message": "nsfw"}},
            },
            None,
        )
        assert failure.status is FeatureStatus.FAILED and failure.error == {"message": "nsfw"}
        processing = parse_record(
            {"uuid": "r3", "status": "PROCESSING", "aiRecordDetail": {"resultObject": []}}, None
        )
        assert not processing.done

    def test_catalog_loads(self) -> None:
        catalog = StaticFeatureCatalog.load_default()
        spec = catalog.get("content_translator")
        assert spec is not None and spec.conversation_id == "type"
        assert {"IMAGE_GENERATOR", "TEXT_TO_SPEECH", "SPEECH_TO_TEXT", "TEXT_TO_VIDEO"} <= {
            s.type for s in catalog.list()
        }


class TestDownloader:
    async def test_refuses_unsafe_urls(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200))
        ) as client:
            downloader = ResultDownloader(client, allowed_host_suffixes=("storage.example",))
            for url in (
                "http://storage.example/a",
                "https://127.0.0.1/a",
                "https://evil.example/a",
            ):
                with pytest.raises(UpstreamError):
                    await downloader.download(url, max_bytes=10)

    async def test_size_limit_and_redirects(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/redirect":
                return httpx.Response(302, headers={"location": "https://127.0.0.1/"})
            return httpx.Response(200, content=b"x" * 100)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            downloader = ResultDownloader(client)
            with pytest.raises(Exception, match="larger"):
                await downloader.download("https://storage.example/big", max_bytes=10)
            with pytest.raises(UpstreamError):
                await downloader.download("https://storage.example/redirect", max_bytes=1000)
            content, _ = await downloader.download("https://storage.example/ok", max_bytes=1000)
            assert content == b"x" * 100

    async def test_timeout(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow", request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(UpstreamTimeoutError):
                await ResultDownloader(client).download("https://storage.example/x", max_bytes=10)


class TestApiKeys:
    def test_entries_and_verification(self) -> None:
        key = generate_key()
        entries = parse_key_entries(f"agent:{hash_key(key)}:30\n# comment\nother:{'a' * 64}")
        verifier = StaticApiKeyVerifier(entries)
        assert verifier.verify(key) == ClientIdentity("agent", 30)
        assert verifier.verify(f"  {key} ") == ClientIdentity("agent", 30)
        assert verifier.verify("gw-wrong") is None

    def test_plain_keys_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="SHA-256"):
            parse_key_entries("agent:gw-my-secret-key")


class TestRateLimiter:
    def test_token_bucket(self) -> None:
        now = [0.0]
        limiter = TokenBucketLimiter(default_rpm=2, clock=lambda: now[0])
        client = ClientIdentity("a")
        assert limiter.acquire(client) is None
        assert limiter.acquire(client) is None
        wait = limiter.acquire(client)
        assert wait == pytest.approx(30.0)
        now[0] = 30.0
        assert limiter.acquire(client) is None
        assert TokenBucketLimiter(default_rpm=0).acquire(client) is None


def test_invalid_request_error_is_a_gateway_error() -> None:
    assert InvalidRequestError("x").kind is ErrorKind.INVALID_REQUEST
