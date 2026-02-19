# tests/conftest_fastapi.py
"""
Configuration des tests pour FastAPI.
Ce fichier remplace conftest.py pour l'application FastAPI.
"""

import os
import sys
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ajouter src au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ============================================================================
# FIXTURES: Application FastAPI
# ============================================================================
@pytest.fixture(scope="session")
def app():
    """Application FastAPI pour les tests."""
    from src.api.app import create_app

    app_instance, logger = create_app()
    return app_instance


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Client de test async pour FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ============================================================================
# FIXTURES: Authentication
# ============================================================================
@pytest.fixture
def valid_api_key() -> str:
    """Clé API valide pour les tests."""
    return "test-api-key-64chars-" + "x" * 44


@pytest.fixture
def invalid_api_key() -> str:
    """Clé API invalide (trop courte)."""
    return "short-key"


@pytest.fixture
def auth_headers(valid_api_key) -> dict[str, str]:
    """Headers avec API-KEY (format 1min.ai)."""
    return {
        "API-KEY": valid_api_key,
        "Content-Type": "application/json",
    }


@pytest.fixture
def bearer_headers(valid_api_key) -> dict[str, str]:
    """Headers avec Bearer token (format OpenAI)."""
    return {
        "Authorization": f"Bearer {valid_api_key}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def no_auth_headers() -> dict[str, str]:
    """Headers sans authentification."""
    return {"Content-Type": "application/json"}


# ============================================================================
# FIXTURES: Request Data
# ============================================================================
@pytest.fixture
def simple_chat_request() -> dict[str, Any]:
    """Requête chat simple."""
    return {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }


@pytest.fixture
def streaming_chat_request() -> dict[str, Any]:
    """Requête chat en streaming."""
    return {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }


@pytest.fixture
def multimodal_chat_request() -> dict[str, Any]:
    """Requête avec image (multimodal)."""
    return {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                        },
                    },
                ],
            }
        ],
        "stream": False,
    }


@pytest.fixture
def empty_messages_request() -> dict[str, Any]:
    """Requête sans messages."""
    return {"model": "gpt-4o", "messages": []}


@pytest.fixture
def no_content_request() -> dict[str, Any]:
    """Requête avec message vide."""
    return {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": ""}],
    }


# ============================================================================
# FIXTURES: Domain Objects
# ============================================================================
@pytest.fixture
def chat_request_factory(valid_api_key):
    """Factory pour créer des ChatRequest."""
    from src.domain.ports import ChatRequest

    def _create(
        api_key: str = None,
        model: str = "gpt-4o",
        messages: list = None,
        stream: bool = False,
        extra_params: dict = None,
    ):
        return ChatRequest(
            api_key=api_key or valid_api_key,
            model=model,
            messages=messages or [{"role": "user", "content": "Hello"}],
            stream=stream,
            extra_params=extra_params,
        )

    return _create


# ============================================================================
# FIXTURES: Mock Services
# ============================================================================
@pytest.fixture
def mock_asset_service():
    """Mock du AssetServicePort."""
    mock = MagicMock()
    mock.upload_image.return_value = "/uploads/test-image.png"
    return mock


@pytest.fixture
def mock_conversation_service():
    """Mock du ConversationServicePort."""
    mock = MagicMock()
    mock.create_conversation.return_value = "test-uuid-12345678"
    return mock


@pytest.fixture
def mock_token_service():
    """Mock du TokenServicePort."""
    mock = MagicMock()
    mock.calculate.return_value = 10
    return mock


@pytest.fixture
def chat_service(mock_asset_service, mock_conversation_service, mock_token_service):
    """ChatService avec mocks injectés."""
    from src.domain.services.chat_service import ChatService

    return ChatService(
        asset_service=mock_asset_service,
        conversation_service=mock_conversation_service,
        token_service=mock_token_service,
        available_models=["gpt-4o", "gpt-4o-mini", "claude-3-haiku", "mistral-medium-latest"],
    )


# ============================================================================
# FIXTURES: Mock Responses API 1min.ai
# ============================================================================
@pytest.fixture
def mock_1min_success_response() -> dict[str, Any]:
    """Réponse réussie de l'API 1min.ai."""
    return {
        "aiRecord": {
            "aiRecordDetail": {
                "resultObject": ["Bonjour ! Comment puis-je vous aider aujourd'hui ?"]
            }
        }
    }


@pytest.fixture
def mock_1min_streaming_lines() -> list[bytes]:
    """Lignes de streaming de l'API 1min.ai."""
    return [
        b'data: {"result": "Bonjour"}',
        b'data: {"result": " !"}',
        b'data: {"result": " Comment"}',
        b'data: {"result": " puis-je"}',
        b'data: {"result": " vous"}',
        b'data: {"result": " aider"}',
        b'data: {"result": " ?"}',
        b"data: [DONE]",
    ]


# ============================================================================
# FIXTURES: Test Data
# ============================================================================
@pytest.fixture
def sample_base64_image() -> str:
    """Image PNG 1x1 pixel en base64."""
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


@pytest.fixture
def youtube_url() -> str:
    """URL YouTube valide."""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def available_models() -> list[str]:
    """Liste des modèles disponibles pour les tests."""
    return ["gpt-4o", "gpt-4o-mini", "claude-3-haiku", "mistral-medium-latest"]


# ============================================================================
# HELPERS: Assertions personnalisées
# ============================================================================
class APIAssertions:
    """Helpers pour assertions sur les réponses API."""

    @staticmethod
    def assert_success(response, expected_model: str = None):
        """Vérifie une réponse réussie."""
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert "id" in data
        assert data["id"].startswith("chatcmpl-")
        assert "usage" in data
        if expected_model:
            assert data["model"] == expected_model

    @staticmethod
    def assert_error(response, expected_status: int, expected_code: str = None):
        """Vérifie une réponse d'erreur."""
        assert response.status_code == expected_status
        data = response.json()
        assert "error" in data or "detail" in data
        if expected_code:
            error_data = data.get("error") or data.get("detail", {})
            if isinstance(error_data, dict):
                assert "code" in error_data

    @staticmethod
    def assert_openai_format(data: dict):
        """Vérifie le format OpenAI."""
        required_fields = ["id", "object", "created", "model", "choices", "usage"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        assert data["object"] == "chat.completion"


@pytest.fixture
def api_assert():
    """Fixture pour les assertions API."""
    return APIAssertions()


# ============================================================================
# FIXTURES: Result Pattern
# ============================================================================
@pytest.fixture
def success_class():
    """Classe Success pour les tests."""
    from src.application.use_cases import Success

    return Success


@pytest.fixture
def failure_class():
    """Classe Failure pour les tests."""
    from src.application.use_cases import Failure

    return Failure
