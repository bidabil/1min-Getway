# tests/conftest.py
"""
Configuration centralisée des tests.
Fixtures réutilisables pour toute la suite de tests.
Supporte à la fois Flask (legacy) et FastAPI.
"""

import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

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


@pytest.fixture
def client(app):
    """Client de test synchrone pour FastAPI (via TestClient)."""
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
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
def conversation_messages() -> list[dict[str, str]]:
    """Messages de conversation multi-tours."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there! How can I help you?"},
        {"role": "user", "content": "What is the weather today?"},
    ]


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


@pytest.fixture
def conversation_context_factory():
    """Factory pour créer des ConversationContext."""
    from src.domain.ports import ConversationContext

    def _create(
        type: str = "CHAT_WITH_AI",
        session_id: str = None,
        image_paths: list = None,
        prompt_object: dict = None,
    ):
        return ConversationContext(
            type=type,
            session_id=session_id,
            image_paths=image_paths or [],
            prompt_object=prompt_object or {"prompt": "Test", "isMixed": False, "webSearch": False},
        )

    return _create


# ============================================================================
# FIXTURES: Mock Services (Ports)
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
# FIXTURES: HTTP Mocks
# ============================================================================
@pytest.fixture
def mock_http_response(mock_1min_success_response):
    """Mock d'une réponse HTTP réussie."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = mock_1min_success_response
    mock.raise_for_status = MagicMock()
    mock.headers = {"Content-Type": "application/json"}
    return mock


@pytest.fixture
def mock_http_streaming_response(mock_1min_streaming_lines):
    """Mock d'une réponse HTTP streaming."""
    mock = MagicMock()
    mock.status_code = 200
    mock.iter_lines.return_value = iter(mock_1min_streaming_lines)
    mock.raise_for_status = MagicMock()
    mock.headers = {"Content-Type": "text/event-stream"}
    return mock


@pytest.fixture
def mock_requests_post(mock_http_response):
    """Mock requests.post global."""
    with patch("requests.post") as mock:
        mock.return_value = mock_http_response
        yield mock


# ============================================================================
# FIXTURES: Test Data
# ============================================================================
@pytest.fixture
def sample_base64_image() -> str:
    """Image PNG 1x1 pixel en base64."""
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_external_image_url() -> str:
    """URL d'image externe."""
    return "https://example.com/image.jpg"


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
    def assert_streaming(response):
        """Vérifie une réponse streaming."""
        assert response.status_code == 200
        content = response.text
        assert "data:" in content

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
# HELPERS: Result Pattern
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
