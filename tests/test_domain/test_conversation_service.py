# tests/test_domain/test_conversation_service.py
"""
Tests pour le service de gestion des conversations.
"""
import pytest


class TestConversationService:
    """Tests pour le service de conversations."""

    def test_format_conversation_history_simple_text(self):
        """Test avec un simple texte."""
        from src.domain.conversation_service import format_conversation_history

        messages = []
        new_input = "Bonjour, comment ça va ?"

        result = format_conversation_history(messages, new_input)

        assert result == "Bonjour, comment ça va ?"
        assert isinstance(result, str)

    def test_format_conversation_history_openai_format(self):
        """Test avec le format OpenAI (liste de parties)."""
        from src.domain.conversation_service import format_conversation_history

        messages = []
        new_input = [
            {"type": "text", "text": "Bonjour"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
            {"type": "text", "text": "comment ça va ?"},
        ]

        result = format_conversation_history(messages, new_input)

        assert result == "Bonjour comment ça va ?"
        assert "image_url" not in result

    def test_format_conversation_history_empty_input(self):
        """Test avec une entrée vide."""
        from src.domain.conversation_service import format_conversation_history

        messages = []
        new_input = ""

        result = format_conversation_history(messages, new_input)

        assert result == ""

    def test_format_conversation_history_only_images(self):
        """Test avec seulement des images (pas de texte)."""
        from src.domain.conversation_service import format_conversation_history

        messages = []
        new_input = [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
        ]

        result = format_conversation_history(messages, new_input)

        assert result == ""  # Pas de texte

    def test_format_conversation_history_mixed_content(self):
        """Test avec un contenu mixte."""
        from src.domain.conversation_service import format_conversation_history

        messages = []
        new_input = [
            {"type": "text", "text": "Regarde"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
            {"type": "text", "text": "cette image."},
        ]

        result = format_conversation_history(messages, new_input)

        assert result == "Regarde cette image."

    def test_format_conversation_history_string_input(self):
        """Test avec une entrée qui est déjà une chaîne."""
        from src.domain.conversation_service import format_conversation_history

        messages = []
        new_input = "Simple string input"

        result = format_conversation_history(messages, new_input)

        assert result == "Simple string input"

    def test_format_conversation_history_with_actual_messages(self):
        """Test avec des messages réels (bien que non utilisés)."""
        from src.domain.conversation_service import format_conversation_history

        messages = [
            {"role": "user", "content": "Premier message"},
            {"role": "assistant", "content": "Réponse"},
            {"role": "user", "content": "Dernier message"},
        ]
        new_input = "Nouveau message"

        result = format_conversation_history(messages, new_input)

        # Note: Le service ignore les messages passés, prend seulement new_input
        assert result == "Nouveau message"
