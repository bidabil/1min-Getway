"""ASGI entry point: `uvicorn gateway.main:app`."""

from .config import Settings
from .infrastructure.observability.logging import configure_logging
from .interfaces.http.app import create_app

_settings = Settings()
configure_logging(_settings.log_level, _settings.log_format)
app = create_app(_settings)
