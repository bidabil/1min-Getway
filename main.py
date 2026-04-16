# main.py
"""
Point d'entrée FastAPI pour 1min-Gateway.
"""

import os
import socket

import uvicorn

from src.api.app import create_app
from src.config import APP_HOST, APP_PORT, WORKERS
from src.infrastructure.logging_config import get_logger, setup_logging

# Configuration du logging structuré
# JSON_LOGS=true pour le format JSON (production)
# JSON_LOGS=false pour le format texte (développement)
json_logs = os.getenv("JSON_LOGS", "false").lower() == "true"
setup_logging(json_format=json_logs)

# Création de l'application FastAPI
app, _ = create_app()

# Logger structuré
logger = get_logger("1min-gateway.main")

if __name__ == "__main__":
    local_ip: str = socket.gethostbyname(socket.gethostname())
    logger.info(
        "Gateway starting",
        host=local_ip,
        port=APP_PORT,
        workers=WORKERS,
        docs_url=f"http://localhost:{APP_PORT}/docs",
        redoc_url=f"http://localhost:{APP_PORT}/redoc",
    )

    uvicorn.run(
        "main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=False,
        workers=WORKERS,
        log_level="info",
        access_log=True,
    )
