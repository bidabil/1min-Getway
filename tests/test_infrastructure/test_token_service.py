# tests/test_infrastructure/test_token_service.py
"""
Tests pour le service de calcul de tokens.
"""
from unittest.mock import MagicMock, patch

import pytest


class TestTokenService:
    """Tests pour le calcul de tokens."""

    def test_calculate_token_empty_string(self):
        """Test avec une chaîne vide."""
        from src.infrastructure.token_service import calculate_token

        result = calculate_token("")
        assert result == 0

    def test_calculate_token_openai_model(self):
        """Test avec un modèle OpenAI."""
        from src.infrastructure.token_service import calculate_token

        text = "Bonjour, comment ça va ?"
        result = calculate_token(text, "gpt-4o")

        assert isinstance(result, int)
        assert result > 0

    def test_calculate_token_mistral_model(self):
        """Test avec un modèle Mistral."""
        from src.infrastructure.token_service import calculate_token

        text = "Bonjour, comment ça va ?"
        result = calculate_token(text, "mistral-medium-latest")

        assert isinstance(result, int)
        assert result > 0

    def test_calculate_token_claude_model(self):
        """Test avec un modèle Claude."""
        from src.infrastructure.token_service import calculate_token

        text = "Bonjour, comment ça va ?"
        result = calculate_token(text, "claude-3-haiku")

        assert isinstance(result, int)
        assert result > 0

    def test_calculate_token_unknown_model(self):
        """Test avec un modèle inconnu (fallback)."""
        from src.infrastructure.token_service import calculate_token

        text = "Bonjour, comment ça va ?"
        result = calculate_token(text, "unknown-model-123")

        assert isinstance(result, int)
        assert result > 0

    def test_calculate_token_long_text(self):
        """Test avec un texte long."""
        from src.infrastructure.token_service import calculate_token

        text = "Lorem ipsum " * 100  # 1200 caractères
        result = calculate_token(text, "gpt-4o")

        assert isinstance(result, int)
        # L'estimation est approximative, donc on met une plage
        assert 150 <= result <= 350  # Plage plus large

    @patch("src.infrastructure.token_service.tiktoken.encoding_for_model")
    def test_calculate_token_encoding_error(self, mock_encoding):
        """Test quand l'encodage échoue."""
        from src.infrastructure.token_service import calculate_token

        # Simuler une erreur KeyError
        mock_encoding.side_effect = KeyError("Unknown model")

        text = "Test text"
        result = calculate_token(text, "unknown-model")

        assert isinstance(result, int)
        assert result > 0

    @patch("src.infrastructure.token_service.MistralTokenizer.from_model")
    def test_calculate_token_mistral_error(self, mock_tokenizer):
        """Test quand le tokenizer Mistral échoue."""
        from src.infrastructure.token_service import calculate_token

        # Simuler une erreur
        mock_tokenizer.side_effect = Exception("Mistral error")

        text = "Test text"
        result = calculate_token(text, "mistral-medium-latest")

        # Devrait tomber en fallback
        assert isinstance(result, int)
        assert result > 0
