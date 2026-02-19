# src/api/app.py
"""
Application Factory FastAPI pour 1min-Gateway.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

import coloredlogs
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from ..config import (
    CORS_ORIGINS,
    MEMCACHED_HOST,
    MEMCACHED_PORT,
    RATELIMIT_DEFAULT,
    RATELIMIT_ENABLED,
)
from .routes import router


def check_memcached_connection(
    host: str | None = None,
    port: int | None = None,
) -> bool:
    """Vérifie la disponibilité de Memcached."""
    from pymemcache.client.base import Client

    effective_host: str = host or MEMCACHED_HOST
    effective_port: int = port or MEMCACHED_PORT

    try:
        client = Client((effective_host, effective_port), connect_timeout=2, timeout=2)
        client.set("health_check", "ok")
        result = client.get("health_check")
        return bool(result == b"ok")
    except Exception:
        return False


def setup_logging() -> logging.Logger:
    """Configure le logging."""
    logger = logging.getLogger("1min-gateway")
    logger.setLevel(logging.DEBUG)

    if not os.path.exists("logs"):
        os.makedirs("logs")

    coloredlogs.install(
        level="DEBUG",
        logger=logger,
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

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

    # Vérification Memcached
    if check_memcached_connection():
        logger.info("LIMITER | Backend: Memcached (Distribué) ✅")
    else:
        logger.warning("LIMITER | Memcached indisponible. Backend: IN-MEMORY ⚠️")

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if CORS_ORIGINS == "*" else CORS_ORIGINS.split(","),
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
