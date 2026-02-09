# tests/test_infrastructure/test_token_service.py
"""
Tests pour le service de calcul de tokens.
"""

from unittest.mock import patch

import pytest


class TestCalculateToken:
    """Tests pour calculate_token."""

    @pytest.fixture
    def calculate_fn(self):
        from src.infrastructure.token_service import calculate_token

        return calculate_token

    # --- Tests de base ---
    def test_returns_zero_for_empty_string(self, calculate_fn):
        # Act
        result = calculate_fn("")

        # Assert
        assert result == 0

    def test_returns_integer(self, calculate_fn):
        # Act
        result = calculate_fn("Hello world", "gpt-4o")

        # Assert
        assert isinstance(result, int)
        assert result > 0

    # --- Tests par fournisseur ---
    def test_openai_model(self, calculate_fn):
        # Arrange
        text = "Bonjour, comment ça va ?"

        # Act
        result = calculate_fn(text, "gpt-4o")

        # Assert
        assert result > 0

    def test_openai_mini_model(self, calculate_fn):
        # Arrange
        text = "Bonjour, comment ça va ?"

        # Act
        result = calculate_fn(text, "gpt-4o-mini")

        # Assert
        assert result > 0

    def test_mistral_model(self, calculate_fn):
        # Arrange
        text = "Bonjour, comment ça va ?"

        # Act
        result = calculate_fn(text, "mistral-medium-latest")

        # Assert
        assert result > 0

    def test_claude_model(self, calculate_fn):
        # Arrange
        text = "Bonjour, comment ça va ?"

        # Act
        result = calculate_fn(text, "claude-3-haiku")

        # Assert
        assert result > 0

    def test_unknown_model_uses_fallback(self, calculate_fn):
        # Arrange
        text = "Bonjour, comment ça va ?"

        # Act
        result = calculate_fn(text, "unknown-model-xyz")

        # Assert
        assert result > 0

    # --- Tests de longueur ---
    def test_long_text(self, calculate_fn):
        # Arrange
        text = "Lorem ipsum dolor sit amet. " * 100

        # Act
        result = calculate_fn(text, "gpt-4o")

        # Assert
        assert result > 100  # Long text = many tokens

    def test_short_text(self, calculate_fn):
        # Arrange
        text = "Hi"

        # Act
        result = calculate_fn(text, "gpt-4o")

        # Assert
        assert result >= 1

    # --- Tests de gestion d'erreurs ---
    @patch("src.infrastructure.token_service.tiktoken.encoding_for_model")
    def test_handles_tiktoken_error_gracefully(self, mock_encoding, calculate_fn):
        # Arrange
        mock_encoding.side_effect = KeyError("Unknown model")

        # Act
        result = calculate_fn("Test text", "gpt-4o")

        # Assert
        assert isinstance(result, int)
        assert result >= 0

    @patch("src.infrastructure.token_service.MistralTokenizer.from_model")
    def test_handles_mistral_tokenizer_error(self, mock_tokenizer, calculate_fn):
        # Arrange
        mock_tokenizer.side_effect = Exception("Mistral error")

        # Act
        result = calculate_fn("Test text", "mistral-medium-latest")

        # Assert
        # Should fall back to estimation
        assert isinstance(result, int)
        assert result >= 0

    # --- Tests paramétrés ---
    @pytest.mark.parametrize(
        "model",
        [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "claude-3-haiku",
            "claude-3-sonnet",
            "mistral-medium-latest",
            "unknown-model",
        ],
    )
    def test_various_models(self, calculate_fn, model):
        # Arrange
        text = "Hello, this is a test message."

        # Act
        result = calculate_fn(text, model)

        # Assert
        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.parametrize(
        "text,min_tokens",
        [
            ("", 0),
            ("Hi", 1),
            ("Hello world", 2),
            ("This is a longer sentence with more tokens.", 5),
        ],
    )
    def test_various_text_lengths(self, calculate_fn, text, min_tokens):
        # Act
        result = calculate_fn(text, "gpt-4o")

        # Assert
        assert result >= min_tokens
