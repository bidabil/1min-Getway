"""MCP server (streamable HTTP, mounted at /mcp) exposing 1min.ai features as agent tools.

Every MCP HTTP request is authenticated with a gateway API key, like the REST APIs.
"""

import base64
import binascii
from collections.abc import Awaitable
from dataclasses import replace
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.datastructures import Headers
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from ... import __version__
from ...application.access import ClientAccess
from ...bootstrap import Container
from ...domain.chat import ChatRequest, ImagePart, Message, TextPart, WebSearch
from ...domain.errors import GatewayError
from ...domain.features import FeatureRecord, FeatureRequest
from ...domain.media import FileUpload, ImageGenerationRequest, SpeechRequest, TranscriptionRequest
from ...infrastructure.observability.logging import client_var
from ..http.dependencies import extract_api_key
from ..http.errors import error_response
from ..http.routes.features import record_body, spec_body

INSTRUCTIONS = """\
Tools backed by 1min.ai. Use them for capabilities your own model lacks: image generation
and editing, speech synthesis and transcription, live web search, image understanding,
YouTube summaries, translation, and any other 1min.ai feature (list_features, run_feature).
Files must be uploaded first with upload_file; pass the returned asset_key to other tools.
Long jobs (video, music) may return status "processing": poll get_feature_result.
"""


async def _guard[T](awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except GatewayError as exc:
        raise ToolError(exc.message) from exc


def build_mcp_server(container: Container) -> MCPServer:
    settings = container.settings
    server: MCPServer = MCPServer(
        name="1min-gateway", version=__version__, instructions=INSTRUCTIONS
    )

    @server.tool(
        description="List the 1min.ai feature types with their models and promptObject fields."
    )
    async def list_features(category: str | None = None) -> list[dict[str, Any]]:
        """category: optional filter (image, audio, video, writing, code)."""
        return [
            spec_body(spec)
            for spec in container.features.catalog()
            if category is None or spec.category == category.lower()
        ]

    @server.tool(
        description=(
            "Run any 1min.ai feature (e.g. TEXT_TO_VIDEO, MUSIC_GENERATOR, BACKGROUND_REMOVER, "
            "SUMMARIZER) with its promptObject. With wait=true the tool waits up to timeout_s "
            "for the result; otherwise it returns a record id to poll with get_feature_result."
        )
    )
    async def run_feature(
        feature_type: str,
        prompt_object: dict[str, Any],
        model: str | None = None,
        wait: bool = True,
        timeout_s: float = 300.0,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = container.features.catalog()
        resolved_model = model or next(
            (s.models[0] for s in spec if s.type == feature_type.upper() and s.models), None
        )
        if not resolved_model:
            raise ToolError("A model is required for this feature (see list_features).")
        request = FeatureRequest(
            type=feature_type, model=resolved_model, prompt_object=prompt_object, extra=extra or {}
        )
        if wait:
            timeout = min(max(timeout_s, 1.0), 900.0)
            record = await _guard(container.features.run_and_wait(request, timeout_s=timeout))
        else:
            record = await _guard(container.features.run(replace(request, run_async=True)))
        return record_body(record)

    @server.tool(description="Get the status and result of a feature started with run_feature.")
    async def get_feature_result(record_id: str) -> dict[str, Any]:
        return record_body(await _guard(container.features.result(record_id)))

    @server.tool(
        description="Generate images from a text prompt. Returns signed URLs and asset keys."
    )
    async def generate_image(
        prompt: str,
        model: str | None = None,
        size: str | None = "1024x1024",
        n: int = 1,
        quality: str | None = None,
    ) -> dict[str, Any]:
        result = await _guard(
            container.images.generate(
                ImageGenerationRequest(
                    prompt=prompt,
                    model=model or settings.default_image_model,
                    n=n,
                    size=size,
                    quality=quality,
                )
            )
        )
        return {
            "images": [{"url": image.url, "asset_key": image.asset_key} for image in result.images],
            "record_id": result.record_id,
        }

    @server.tool(description="Convert text to speech. Returns a signed URL of the audio file.")
    async def text_to_speech(
        text: str,
        voice: str = "alloy",
        model: str | None = None,
        response_format: str = "mp3",
    ) -> dict[str, Any]:
        url = await _guard(
            container.audio.speech_url(
                SpeechRequest(
                    text=text,
                    model=model or settings.default_tts_model,
                    voice=voice,
                    response_format=response_format,
                )
            )
        )
        return {"url": url, "format": response_format}

    @server.tool(
        description="Transcribe an audio file previously uploaded with upload_file (asset_key)."
    )
    async def transcribe_audio(
        asset_key: str, language: str | None = None, model: str | None = None
    ) -> str:
        result = await _guard(
            container.audio.transcribe(
                TranscriptionRequest(
                    audio=asset_key,
                    model=model or settings.default_stt_model,
                    language=language,
                    response_format="text",
                )
            )
        )
        return result.text

    @server.tool(
        description="Upload a file (base64) to 1min.ai. Returns the asset_key and file_id to use with other tools."
    )
    async def upload_file(
        filename: str,
        content_base64: str,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        try:
            content = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError):
            raise ToolError("content_base64 is not valid base64.") from None
        asset = await _guard(container.files.upload(FileUpload(filename, content, content_type)))
        return {"asset_key": asset.reference, "file_id": asset.file_id, "size": asset.size}

    @server.tool(
        description="Answer a question using live web search (1min.ai). Returns the answer text."
    )
    async def web_search(query: str, model: str | None = None, sites: int = 3) -> str:
        return await _chat_text(
            container,
            ChatRequest(
                model=model or settings.default_tool_model,
                messages=(Message(role="user", content=(TextPart(query),)),),
                web_search=WebSearch(sites=min(max(sites, 1), 10)),
            ),
        )

    @server.tool(
        description="Ask a vision model about an image given as https URL, data: URI or asset_key."
    )
    async def analyze_image(image: str, question: str, model: str | None = None) -> str:
        return await _chat_text(
            container,
            ChatRequest(
                model=model or settings.default_tool_model,
                messages=(Message(role="user", content=(TextPart(question), ImagePart(image))),),
            ),
        )

    @server.tool(description="Summarize a YouTube video.")
    async def summarize_youtube(
        url: str, language: str = "English", model: str | None = None
    ) -> str:
        record = await _guard(
            container.features.run_and_wait(
                FeatureRequest(
                    type="YOUTUBE_SUMMARIZER",
                    model=model or "gpt-4o",
                    prompt_object={"videoUrl": url, "language": language},
                    extra={"videoUrl": url},
                ),
                timeout_s=settings.feature_timeout_s,
            )
        )
        return _record_text(record)

    @server.tool(
        description="Translate text into the target language (ISO code such as fr, en, es)."
    )
    async def translate_text(
        text: str,
        target_language: str,
        source_language: str = "auto",
        tone: str = "neutral",
        domain: str = "General",
        writing_style: str = "Standard",
        model: str | None = None,
    ) -> str:
        record = await _guard(
            container.features.run_and_wait(
                FeatureRequest(
                    type="CONTENT_TRANSLATOR",
                    model=model or "gpt-4o",
                    prompt_object={
                        "prompt": text,
                        "originalLanguage": source_language,
                        "targetLanguage": target_language,
                        "tone": tone,
                        "domain": domain,
                        "writingStyle": writing_style,
                    },
                ),
                timeout_s=settings.feature_timeout_s,
            )
        )
        return _record_text(record)

    return server


async def _chat_text(container: Container, request: ChatRequest) -> str:
    result = await _guard(container.chat.complete(request))
    return result.text or result.refusal or ""


def _record_text(record: FeatureRecord) -> str:
    if record.status.value == "failed":
        message = record.error.get("message") if record.error else None
        raise ToolError(f"1min.ai could not complete the request: {message or 'unknown error'}.")
    if record.status.value == "processing":
        raise ToolError(f"Still processing; poll get_feature_result with record_id={record.id}.")
    text = record.first_text()
    if text is None:
        raise ToolError("1min.ai returned no text.")
    return text


class McpAuthGuard:
    """ASGI wrapper authenticating every MCP request with a gateway API key."""

    def __init__(self, app: ASGIApp, access: ClientAccess) -> None:
        self._app = app
        self._access = access

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        try:
            client = self._access.authorize(extract_api_key(Headers(scope=scope)))
        except GatewayError as exc:
            await error_response(exc, anthropic=False)(scope, receive, send)
            return
        client_var.set(client.name)
        scope.setdefault("state", {})["client"] = client.name
        await self._app(scope, receive, send)


def mcp_route(server: MCPServer, container: Container) -> Route:
    """Build the /mcp route. Must be called once per server (it creates the session manager)."""
    allowed_hosts = list(container.settings.mcp_host_list())
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=bool(allowed_hosts),
        allowed_hosts=allowed_hosts,
        allowed_origins=[f"https://{host}" for host in allowed_hosts]
        + [f"http://{host}" for host in allowed_hosts],
    )
    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=security,
        host="0.0.0.0",  # noqa: S104 - disables the SDK's localhost-only default; auth is enforced
    )
    endpoint = next(
        route for route in app.routes if isinstance(route, Route) and route.path == "/mcp"
    ).endpoint
    return Route(
        "/mcp", endpoint=McpAuthGuard(endpoint, container.access), methods=["GET", "POST", "DELETE"]
    )
