# tests/test_application/test_use_cases.py
"""
Tests pour les Use Cases (Application Layer).
Focus sur le comportement métier.
"""

from unittest.mock import MagicMock

import pytest


# ============================================================================
# TESTS: ValidateApiKeyUseCase
# ============================================================================
class TestValidateApiKeyUseCase:
    """Tests pour la validation de clé API."""

    @pytest.fixture
    def use_case(self):
        from src.application.use_cases import ValidateApiKeyUseCase

        return ValidateApiKeyUseCase()

    def test_returns_success_for_valid_key(self, use_case, success_class, valid_api_key):
        result = use_case.execute(valid_api_key)
        assert isinstance(result, success_class)
        assert result.data == valid_api_key

    def test_returns_failure_for_empty_key(self, use_case, failure_class):
        result = use_case.execute("")
        assert isinstance(result, failure_class)
        assert result.error_code == "UNAUTHORIZED"

    def test_returns_failure_for_none_key(self, use_case, failure_class):
        result = use_case.execute(None)
        assert isinstance(result, failure_class)
        assert result.error_code == "UNAUTHORIZED"

    def test_returns_failure_for_short_key(self, use_case, failure_class, invalid_api_key):
        result = use_case.execute(invalid_api_key)
        assert isinstance(result, failure_class)
        assert "Invalid" in result.message


# ============================================================================
# TESTS: ChatCompletionUseCase
# ============================================================================
class TestChatCompletionUseCase:
    """Tests pour le use case de chat completion."""

    @pytest.fixture
    def mock_service(self):
        """Mock frais pour chaque test."""
        mock = MagicMock()
        mock.validate_model.return_value = True
        mock.calculate_tokens.return_value = 10
        return mock

    @pytest.fixture
    def use_case(self, mock_service):
        from src.application.use_cases import ChatCompletionUseCase

        return ChatCompletionUseCase(mock_service)

    def test_returns_success_for_valid_request(
        self, use_case, mock_service, conversation_context_factory, success_class, valid_api_key
    ):
        from src.domain.ports import ChatRequest

        request = ChatRequest(
            api_key=valid_api_key,
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False,
            extra_params=None,
        )
        mock_service.resolve_context.return_value = conversation_context_factory()

        result = use_case.execute(request)

        assert isinstance(result, success_class)
        assert result.data.type == "CHAT_WITH_AI"

    def test_returns_failure_for_invalid_model(
        self, use_case, mock_service, failure_class, valid_api_key
    ):
        from src.domain.ports import ChatRequest

        mock_service.validate_model.return_value = False

        request = ChatRequest(
            api_key=valid_api_key,
            model="invalid-model",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False,
            extra_params=None,
        )

        result = use_case.execute(request)

        assert isinstance(result, failure_class)
        assert result.error_code == "MODEL_NOT_FOUND"

    def test_returns_failure_for_empty_messages(self, failure_class, valid_api_key):
        """Test avec messages vides - utilise un mock et use case complètement frais."""
        from src.application.use_cases import ChatCompletionUseCase
        from src.domain.ports import ChatRequest

        # Mock complètement frais
        fresh_mock = MagicMock()
        fresh_mock.validate_model.return_value = True
        fresh_use_case = ChatCompletionUseCase(fresh_mock)

        request = ChatRequest(
            api_key=valid_api_key,
            model="gpt-4o",
            messages=[],  # Liste vide
            stream=False,
            extra_params=None,
        )

        result = fresh_use_case.execute(request)

        assert isinstance(result, failure_class)
        assert result.error_code == "INVALID_REQUEST"

    def test_returns_failure_for_empty_content(self, use_case, failure_class, valid_api_key):
        from src.domain.ports import ChatRequest

        request = ChatRequest(
            api_key=valid_api_key,
            model="gpt-4o",
            messages=[{"role": "user", "content": ""}],
            stream=False,
            extra_params=None,
        )

        result = use_case.execute(request)

        assert isinstance(result, failure_class)
        assert result.error_code == "INVALID_REQUEST"

    def test_returns_failure_when_context_is_none(
        self, use_case, mock_service, failure_class, valid_api_key
    ):
        from src.domain.ports import ChatRequest

        mock_service.resolve_context.return_value = None

        request = ChatRequest(
            api_key=valid_api_key,
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False,
            extra_params=None,
        )

        result = use_case.execute(request)

        assert isinstance(result, failure_class)
        assert result.error_code == "CONTEXT_ERROR"

    def test_handles_exception_gracefully(
        self, use_case, mock_service, failure_class, valid_api_key
    ):
        from src.domain.ports import ChatRequest

        mock_service.resolve_context.side_effect = Exception("Boom!")

        request = ChatRequest(
            api_key=valid_api_key,
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False,
            extra_params=None,
        )

        result = use_case.execute(request)

        assert isinstance(result, failure_class)
        assert result.error_code == "INTERNAL_ERROR"


# ============================================================================
# TESTS: CalculateTokensUseCase
# ============================================================================
class TestCalculateTokensUseCase:
    """Tests pour le calcul de tokens."""

    @pytest.fixture
    def mock_service(self):
        mock = MagicMock()
        mock.calculate_tokens.return_value = 15
        return mock

    @pytest.fixture
    def use_case(self, mock_service):
        from src.application.use_cases import CalculateTokensUseCase

        return CalculateTokensUseCase(mock_service)

    def test_returns_success_with_token_count(self, use_case, mock_service, success_class):
        mock_service.calculate_tokens.return_value = 15

        result = use_case.execute("Hello world", "gpt-4o")

        assert isinstance(result, success_class)
        assert result.data == 15

    def test_handles_exception(self, use_case, mock_service, failure_class):
        mock_service.calculate_tokens.side_effect = Exception("Error")

        result = use_case.execute("text", "model")

        assert isinstance(result, failure_class)
        assert result.error_code == "TOKEN_ERROR"
