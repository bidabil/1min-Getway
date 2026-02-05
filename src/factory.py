# factory.py

import logging
import os
import warnings
from logging.handlers import RotatingFileHandler

import coloredlogs
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymemcache.client.base import Client

# Suppress flask_limiter warnings to keep the console clean from non-critical noise
warnings.filterwarnings("ignore", category=UserWarning, module="flask_limiter.extension")


def check_memcached_connection(host="memcached", port=11211):
    """
    Attempts a quick connection to Memcached to validate availability.
    Essential for Docker environments to ensure the cache layer is ready.
    """
    try:
        # Short 2s timeout to avoid hanging the entire API boot sequence
        client = Client((host, port), connect_timeout=2, timeout=2)
        client.set("health_check", "ok")
        result = client.get("health_check")
        return result == b"ok"
    except Exception:
        return False


def create_app():
    """
    Application Factory: Initializes Flask, Logging, and Rate Limiting.
    """
    app = Flask(__name__)

    # --- LOGGER CONFIGURATION ---
    logger = logging.getLogger("1min-gateway")
    logger.setLevel(logging.DEBUG)

    # 1. Infrastructure: Ensure logs directory exists for persistence
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # 2. Console Handler: Real-time debugging with colored output for Docker/Local
    coloredlogs.install(
        level="DEBUG",
        logger=logger,
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # 3. File Handler: Long-term audit trail with automatic rotation
    # Limits file size to 5MB and keeps 5 historical backups
    file_handler = RotatingFileHandler(
        "logs/api.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # Restrict file output to INFO to prevent disk bloat from DEBUG/Stream chunks
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # 1min-Gateway Welcome Signature
    logger.info(
        r"""

    ==========================================================
      _  __  __ ___ _   _        ____    _  _____ ______        ___ __   __
     / ||  \/  |_ _| \ | |      / ___|  / \|_   _|  ____\ \      / / \\ \ / /
     | || |\/| || ||  \| |_____| |  _  / _ \ | | |  _|    \ \ /\ / / _ \\ V /
     | || |  | || || |\  |_____| |_| |/ ___ \| | | |___    \ V  V / ___ \| |
     |_||_|  |_|___|_| \_|      \____/_/   \_\_| |______|    \_/\_/_/   \_\_|

    ======================== GATEWAY v1.0 ====================
    """
    )

    # --- RATE LIMITER CONFIGURATION ---
    # Hybrid Strategy: Uses Memcached if available, fallbacks to Memory if standalone
    if check_memcached_connection():
        limiter = Limiter(
            get_remote_address,
            app=app,
            storage_uri="memcached://memcached:11211",
            strategy="fixed-window",
        )
        logger.info("LIMITER | Backend: Memcached (Distributed persistence enabled).")
    else:
        limiter = Limiter(
            get_remote_address,
            app=app,
            storage_uri="memory://",
        )
        logger.warning("LIMITER | Memcached unreachable. Backend: IN-MEMORY (Volatile).")

    return app, logger, limiter
