# src/api/app.py
"""
Application Factory FastAPI pour 1min-Gateway.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from ..config import (
    CORS_ORIGINS,
    RATELIMIT_DEFAULT,
    RATELIMIT_ENABLED,
    REQUEST_TIMEOUT,
)
from .routes import router


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui impose un timeout global sur chaque requête entrante.
    Retourne 504 Gateway Timeout si la requête dépasse REQUEST_TIMEOUT secondes.
    """

    def __init__(self, app: ASGIApp, timeout: int = 120) -> None:
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "success": False,
                    "error": {
                        "code": "REQUEST_TIMEOUT",
                        "message": f"Request exceeded the {self.timeout}s timeout.",
                    },
                },
            )


def setup_logging() -> logging.Logger:
    """Configure le logging."""
    logger = logging.getLogger("1min-gateway")
    logger.setLevel(logging.DEBUG)

    if not os.path.exists("logs"):
        os.makedirs("logs")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        "logs/api.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    logger.info(
        r"""
    ==========================================================
      _  __  __ ___ _   _        ____    _  _____ ______
     / ||  \/  |_ _| \ | |      / ___|  / \|_   _|  ____\ \
    | || |\/| || ||  \| |_____| |  _  / _ \ | | |  _|    \ \ /\ /
    | || |  | || || |\  |_____| |_| |/ ___ \| | | |___    \ V  V
    |_||_|  |_|___|_| \_|      \____/_/   \_\_| |______|    \_/\_/
    ======================== GATEWAY v2.0 (FastAPI) =========
    """
    )

    return logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    logger = logging.getLogger("1min-gateway")
    logger.info("🚀 Démarrage de l'application FastAPI")

    yield

    logger.info("⏹️ Arrêt de l'application FastAPI")


def create_app() -> tuple[FastAPI, logging.Logger]:
    """Crée et configure l'application FastAPI."""

    # Configuration du logging
    logger = setup_logging()

    # Création de l'application FastAPI
    app = FastAPI(
        title="1min-Gateway",
        description="API Gateway pour 1min.ai - Compatible OpenAI",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configuration CORS
    # Handle CORS origins: empty string (no CORS), "*" (wildcard), or comma-separated list
    # Default is empty string (secure) - wildcard requires explicit CORS_ORIGINS="*" setting
    if CORS_ORIGINS == "*":
        # Wildcard is intentional for development - default is secure (empty)
        cors_origins = ["*"]
    elif CORS_ORIGINS:
        cors_origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
    else:
        # Default: no CORS allowed - must be explicitly configured
        cors_origins = []

    # Wildcard CORS is only possible through explicit configuration (CORS_ORIGINS="*")
    # Default is secure (empty string) - see src/config.py
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # nosemgrep: python.fastapi.security.wildcard-cors.wildcard-cors
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configuration Rate Limiting
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[RATELIMIT_DEFAULT] if RATELIMIT_ENABLED else [],
        enabled=RATELIMIT_ENABLED,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Timeout middleware — limite la durée de chaque requête
    app.add_middleware(TimeoutMiddleware, timeout=REQUEST_TIMEOUT)

    # Inclusion des routes
    app.include_router(router)

    logger.info("✅ Application FastAPI configurée avec succès")

    return app, logger


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler pour les erreurs de rate limiting."""
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Please slow down.",
            },
        },
    )
