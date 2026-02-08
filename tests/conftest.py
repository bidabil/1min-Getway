# tests/conftest.py

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ajouter le répertoire src au chemin Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session")
def app():
    """Crée une application Flask pour les tests."""
    from src.factory import create_app  # Import depuis factory

    app_instance, _, _ = create_app()

    app_instance.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DEBUG": True,
        }
    )

    # Désactiver le rate limiting
    from src.factory import create_app

    _, _, limiter = create_app()
    if limiter:
        limiter.enabled = False

    return app_instance


@pytest.fixture
def client(app):
    """Crée un client de test Flask."""
    return app.test_client()


@pytest.fixture
def auth_headers():
    """Retourne des headers d'authentification pour les tests."""
    return {
        "Authorization": "Bearer test-api-key-123",
        "API-KEY": "test-api-key-123",
        "Content-Type": "application/json",
    }


@pytest.fixture
def sample_messages():
    """Retourne des messages de test."""
    return [{"role": "user", "content": "Bonjour, comment ça va ?"}]


@pytest.fixture
def mock_1min_response():
    """Mock une réponse réussie de 1min.ai."""
    return {"aiRecord": {"aiRecordDetail": {"resultObject": ["Réponse de test de l'IA"]}}}


@pytest.fixture(autouse=True)
def mock_external_calls():
    """Mock automatique des appels externes pour tous les tests."""
    # Mock requests.post pour éviter les appels réels
    with patch("requests.post") as mock_post:
        # Configurer le mock par défaut
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aiRecord": {"aiRecordDetail": {"resultObject": ["Réponse mockée"]}}
        }
        mock_response.iter_lines.return_value = [b'data: {"result": "test"}', b"data: [DONE]"]
        mock_post.return_value = mock_response

        yield mock_post


@pytest.fixture
def mock_orchestrator():
    """Mock l'orchestrateur."""
    with patch("src.application.orchestrator.resolve_conversation_context") as mock:
        mock.return_value = {
            "type": "CHAT_WITH_AI",
            "session_id": "CHAT_WITH_AI",
            "prompt_object": {"prompt": "Test prompt"},
        }
        yield mock


@pytest.fixture
def mock_token_calculation():
    """Mock le calcul de tokens."""
    with patch("src.adapters.openai_adapter.calculate_token") as mock:
        mock.return_value = 10
        yield mock
