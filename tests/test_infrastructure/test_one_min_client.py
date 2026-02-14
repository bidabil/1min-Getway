# tests/test_infrastructure/test_one_min_client.py
"""
Tests pour le client 1min.ai.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests


class TestGetRetrySession:
    """Tests pour get_retry_session."""

    def test_creates_session_with_retry_adapter(self):
        from src.infrastructure.one_min_client import get_retry_session

        session = get_retry_session()
        assert session is not None
        assert hasattr(session, "mount")


class TestCircuitBreaker:
    """Tests pour le pattern Circuit Breaker."""

    @pytest.fixture
    def circuit_breaker(self):
        from src.infrastructure.one_min_client import CircuitBreaker

        return CircuitBreaker(failure_threshold=3, timeout=30)

    def test_initial_state_is_closed(self, circuit_breaker):
        assert circuit_breaker.failures == 0
        assert circuit_breaker.opened_at is None
        assert circuit_breaker.is_open() is False

    def test_increments_failure_count(self, circuit_breaker):
        circuit_breaker.call_failed()
        assert circuit_breaker.failures == 1
        assert circuit_breaker.is_open() is False

    def test_opens_after_threshold_reached(self, circuit_breaker):
        for _ in range(3):
            circuit_breaker.call_failed()
        assert circuit_breaker.failures == 3
        assert circuit_breaker.is_open() is True

    def test_resets_on_success(self, circuit_breaker):
        circuit_breaker.call_failed()
        circuit_breaker.call_failed()
        circuit_breaker.call_failed()
        assert circuit_breaker.is_open() is True

        circuit_breaker.call_succeeded()
        assert circuit_breaker.failures == 0
        assert circuit_breaker.opened_at is None
        assert circuit_breaker.is_open() is False

    @pytest.mark.parametrize(
        "failures,expected_open",
        [
            (0, False),
            (1, False),
            (2, False),
            (3, True),
            (4, True),
        ],
    )
    def test_various_failure_counts(self, failures, expected_open):
        from src.infrastructure.one_min_client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, timeout=30)
        for _ in range(failures):
            cb.call_failed()
        assert cb.is_open() == expected_open


class TestCreate1minConversation:
    """Tests pour create_1min_conversation."""

    @pytest.fixture
    def create_fn(self):
        from src.infrastructure.one_min_client import create_1min_conversation

        return create_1min_conversation

    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_creates_conversation_successfully(self, mock_post, create_fn, valid_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"conversation": {"uuid": "test-uuid-123"}}
        mock_post.return_value = mock_response

        result = create_fn(
            api_key=valid_api_key, model="gpt-4o", conv_type="CHAT_WITH_AI", title="Test Session"
        )

        assert result == "test-uuid-123"
        mock_post.assert_called_once()

    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_returns_none_on_http_error(self, mock_post, create_fn, valid_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        result = create_fn(api_key=valid_api_key, model="gpt-4o")
        assert result is None

    # CORRECTION: Le service catch le timeout et retourne None, il ne lève pas d'exception
    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_returns_none_on_timeout(self, mock_post, create_fn, valid_api_key):
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")

        result = create_fn(api_key=valid_api_key, model="gpt-4o")

        # Le service catch le timeout et retourne None
        assert result is None

    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_returns_none_on_network_error(self, mock_post, create_fn, valid_api_key):
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        result = create_fn(api_key=valid_api_key, model="gpt-4o")
        assert result is None

    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_creates_pdf_conversation_with_file_ids(self, mock_post, create_fn, valid_api_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"conversation": {"uuid": "pdf-uuid-456"}}
        mock_post.return_value = mock_response

        result = create_fn(
            api_key=valid_api_key,
            model="gpt-4o",
            conv_type="CHAT_WITH_PDF",
            title="PDF Session",
            file_ids=["file-1", "file-2"],
        )

        assert result == "pdf-uuid-456"

    @patch("src.infrastructure.one_min_client.requests.Session.post")
    def test_creates_youtube_conversation_with_url(
        self, mock_post, create_fn, valid_api_key, youtube_url
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"conversation": {"uuid": "yt-uuid-789"}}
        mock_post.return_value = mock_response

        result = create_fn(
            api_key=valid_api_key,
            model="gpt-4o",
            conv_type="CHAT_WITH_YOUTUBE_VIDEO",
            title="YouTube Session",
            youtube_url=youtube_url,
        )

        assert result == "yt-uuid-789"


class TestGetSafePayload:
    """Tests pour _get_safe_payload."""

    @pytest.fixture
    def safe_payload_fn(self):
        from src.infrastructure.one_min_client import _get_safe_payload

        return _get_safe_payload

    def test_redacts_sensitive_keys(self, safe_payload_fn):
        payload = {
            "API-KEY": "secret-key",
            "TOKEN": "secret-token",
            "password": "secret-password",  # pragma: allowlist secret
            "normal_field": "normal-value",
        }

        result = safe_payload_fn(payload)

        assert result["API-KEY"] == "[REDACTED]"
        assert result["TOKEN"] == "[REDACTED]"
        assert result["password"] == "[REDACTED]"
        assert result["normal_field"] == "normal-value"

    def test_preserves_non_sensitive_fields(self, safe_payload_fn):
        payload = {
            "model": "gpt-4o",
            "type": "CHAT_WITH_AI",
            "promptObject": {"prompt": "Hello"},
        }

        result = safe_payload_fn(payload)
        assert result == payload

    def test_handles_empty_payload(self, safe_payload_fn):
        result = safe_payload_fn({})
        assert result == {}
