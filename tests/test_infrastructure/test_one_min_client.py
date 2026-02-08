# tests/test_infrastructure/test_one_min_client.py
"""
Tests pour le client 1min.ai.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestOneMinClient:
    """Tests pour le client 1min.ai."""

    def test_get_retry_session(self):
        """Test la création d'une session avec retry."""
        from src.infrastructure.one_min_client import get_retry_session

        session = get_retry_session()

        assert session is not None
        assert hasattr(session, "mount")

    def test_circuit_breaker_initial_state(self):
        """Test l'état initial du circuit breaker."""
        from src.infrastructure.one_min_client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, timeout=30)

        assert cb.failures == 0
        assert cb.opened_at is None
        assert cb.is_open() is False

    def test_circuit_breaker_call_failed(self):
        """Test l'enregistrement d'un échec."""
        from src.infrastructure.one_min_client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, timeout=30)

        cb.call_failed()
        assert cb.failures == 1
        assert cb.is_open() is False

        cb.call_failed()  # Déclenche le circuit breaker
        assert cb.failures == 2
        assert cb.is_open() is True

    def test_circuit_breaker_call_succeeded(self):
        """Test la réinitialisation après un succès."""
        from src.infrastructure.one_min_client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, timeout=30)

        cb.call_failed()
        cb.call_failed()
        assert cb.is_open() is True

        cb.call_succeeded()
        assert cb.failures == 0
        assert cb.opened_at is None
        assert cb.is_open() is False

    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_create_1min_conversation_success(self, mock_post):
        """Test la création réussie d'une conversation."""
        from src.infrastructure.one_min_client import create_1min_conversation

        # Mock la réponse
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"conversation": {"uuid": "test-uuid-123"}}
        mock_post.return_value = mock_response

        result = create_1min_conversation(
            api_key="test-key", model="gpt-4o", conv_type="CHAT_WITH_AI", title="Test Session"
        )

        assert result == "test-uuid-123"
        mock_post.assert_called_once()

    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_create_1min_conversation_http_error(self, mock_post):
        """Test avec une erreur HTTP."""
        from src.infrastructure.one_min_client import create_1min_conversation

        # Mock une erreur 400
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        result = create_1min_conversation(api_key="test-key", model="gpt-4o")

        assert result is None

    # Dans tests/test_infrastructure/test_one_min_client.py
    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_create_1min_conversation_timeout(self, mock_post):
        """Test avec un timeout."""
        from src.infrastructure.one_min_client import create_1min_conversation

        mock_post.side_effect = requests.exceptions.Timeout("Timeout")

        # La fonction lève Timeout, pas ConnectionError
        with pytest.raises(requests.exceptions.Timeout):
            create_1min_conversation(api_key="test-key", model="gpt-4o")

    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_create_1min_conversation_network_error(self, mock_post):
        """Test avec une erreur réseau."""
        from src.infrastructure.one_min_client import create_1min_conversation

        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        result = create_1min_conversation(api_key="test-key", model="gpt-4o")

        assert result is None

    def test_get_safe_payload(self):
        """Test le masquage des clés sensibles."""
        from src.infrastructure.one_min_client import _get_safe_payload

        payload = {
            "API-KEY": "secret-key",
            "TOKEN": "secret-token",
            "normal_field": "normal-value",
            "password": "secret-password",
        }

        result = _get_safe_payload(payload)

        assert result["API-KEY"] == "[REDACTED]"
        assert result["TOKEN"] == "[REDACTED]"
        assert result["password"] == "[REDACTED]"
        assert result["normal_field"] == "normal-value"
