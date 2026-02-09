# src/factory.py (VERSION OPTIMISÉE)

import logging
import os
import warnings
from logging.handlers import RotatingFileHandler

import coloredlogs
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymemcache.client.base import Client

from .config import MEMCACHED_HOST, MEMCACHED_PORT, RATELIMIT_STORAGE_URL

warnings.filterwarnings("ignore", category=UserWarning, module="flask_limiter.extension")


def check_memcached_connection(host=None, port=None):
    """
    Vérifie la disponibilité de Memcached.
    Utilise les valeurs de config.py si non spécifiées.
    """
    host = host or MEMCACHED_HOST
    port = port or MEMCACHED_PORT

    try:
        client = Client((host, port), connect_timeout=2, timeout=2)
        client.set("health_check", "ok")
        result = client.get("health_check")
        return result == b"ok"
    except Exception:
        return False


def create_app():
    """Application Factory: Initialise Flask, Logging et Rate Limiting"""
    app = Flask(__name__)

    # --- LOGGER CONFIGURATION ---
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
    ======================== GATEWAY v1.0 ====================
    """
    )

    # --- RATE LIMITER CONFIGURATION ---
    if check_memcached_connection():
        limiter = Limiter(
            get_remote_address,
            app=app,
            storage_uri=RATELIMIT_STORAGE_URL,  # ✅ Depuis config.py
            strategy="fixed-window",
        )
        logger.info("LIMITER | Backend: Memcached (Distribué) ✅")
    else:
        limiter = Limiter(
            get_remote_address,
            app=app,
            storage_uri="memory://",
        )
        logger.warning("LIMITER | Memcached indisponible. Backend: IN-MEMORY ⚠️")

    from .routes import register_routes

    register_routes(app, limiter)

    return app, logger, limiter
