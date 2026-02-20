# src/api/__init__.py
"""
Module API FastAPI pour 1min-Gateway.
"""

from .app import create_app
from .routes import router

__all__ = ["create_app", "router"]
