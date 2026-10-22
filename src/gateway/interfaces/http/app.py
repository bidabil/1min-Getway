"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ... import __version__
from ...bootstrap import Container, build_container
from ...config import Settings
from ..mcp.server import build_mcp_server, mcp_route
from .errors import register_exception_handlers
from .middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from .routes import chat, features, health, media


def create_app(settings: Settings | None = None, *, container: Container | None = None) -> FastAPI:
    if container is None:
        container = build_container(settings or Settings())
    settings = container.settings
    mcp_server = build_mcp_server(container) if settings.mcp_enabled else None
    route = mcp_route(mcp_server, container) if mcp_server is not None else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            stack.push_async_callback(container.aclose)
            if mcp_server is not None:
                await stack.enter_async_context(mcp_server.session_manager.run())
            yield

    app = FastAPI(
        title="1min-Gateway",
        version=__version__,
        description="OpenAI- and Anthropic-compatible gateway and MCP server for 1min.ai.",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.container = container
    register_exception_handlers(app)

    for router in (health.router, chat.router, media.router, features.router):
        app.include_router(router)
    if route is not None:
        app.router.routes.append(route)

    origins = settings.cors_origin_list()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(RequestContextMiddleware, metrics=container.metrics)
    return app
