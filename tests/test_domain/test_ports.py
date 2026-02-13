# tests/test_domain/test_ports.py
"""
Tests pour les Value Objects et Ports du domaine.
"""

import pytest


class TestChatRequest:
    """Tests pour le Value Object ChatRequest."""

    def test_create_with_required_fields(self):
        # Arrange & Act
        from src.domain.ports import ChatRequest

        request = ChatRequest(
            api_key="test-key",  # pragma: allowlist secret
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Assert
        assert request.api_key == "test-key"  # pragma: allowlist secret
        assert request.model == "gpt-4o"
        assert len(request.messages) == 1
        assert request.stream is False  # Default
        assert request.extra_params == {}  # Default (empty dict)

    def test_create_with_all_fields(self):
        # Arrange & Act
        from src.domain.ports import ChatRequest

        request = ChatRequest(
            api_key="test-key",  # pragma: allowlist secret
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            stream=True,
            extra_params={"temperature": 0.7},
        )

        # Assert
        assert request.stream is True
        assert request.extra_params["temperature"] == 0.7

    def test_messages_is_list(self):
        # Arrange & Act
        from src.domain.ports import ChatRequest

        request = ChatRequest(
            api_key="key",  # pragma: allowlist secret
            model="gpt-4o",
            messages=[
                {"role": "user", "content": "First"},
                {"role": "assistant", "content": "Response"},
                {"role": "user", "content": "Second"},
            ],
        )

        # Assert
        assert isinstance(request.messages, list)
        assert len(request.messages) == 3


class TestConversationContext:
    """Tests pour le Value Object ConversationContext."""

    def test_create_simple_chat_context(self):
        # Arrange & Act
        from src.domain.ports import ConversationContext

        context = ConversationContext(
            type="CHAT_WITH_AI",
            session_id=None,
            image_paths=[],
            prompt_object={"prompt": "Hello", "isMixed": False, "webSearch": False},
        )

        # Assert
        assert context.type == "CHAT_WITH_AI"
        assert context.session_id is None
        assert context.image_paths == []
        assert context.prompt_object["prompt"] == "Hello"

    def test_create_image_chat_context(self):
        # Arrange & Act
        from src.domain.ports import ConversationContext

        context = ConversationContext(
            type="CHAT_WITH_IMAGE",
            session_id=None,
            image_paths=["/uploads/img1.png", "/uploads/img2.png"],
            prompt_object={
                "prompt": "Describe these",
                "imageList": ["/uploads/img1.png", "/uploads/img2.png"],
                "isMixed": False,
                "webSearch": False,
            },
        )

        # Assert
        assert context.type == "CHAT_WITH_IMAGE"
        assert len(context.image_paths) == 2

    def test_create_pdf_context_with_session(self):
        # Arrange & Act
        from src.domain.ports import ConversationContext

        context = ConversationContext(
            type="CHAT_WITH_PDF",
            session_id="uuid-12345678",
            image_paths=[],
            prompt_object={"prompt": "Summarize this PDF"},
        )

        # Assert
        assert context.type == "CHAT_WITH_PDF"
        assert context.session_id == "uuid-12345678"

    def test_create_youtube_context_with_session(self):
        # Arrange & Act
        from src.domain.ports import ConversationContext

        context = ConversationContext(
            type="CHAT_WITH_YOUTUBE_VIDEO",
            session_id="uuid-87654321",
            image_paths=[],
            prompt_object={"prompt": "What is this video about?"},
        )

        # Assert
        assert context.type == "CHAT_WITH_YOUTUBE_VIDEO"
        assert context.session_id is not None


class TestPortInterfaces:
    """Tests pour vérifier que les interfaces sont bien définies."""

    def test_asset_service_port_is_abstract(self):
        # Arrange
        from src.domain.ports import AssetServicePort

        # Act & Assert
        with pytest.raises(TypeError):
            AssetServicePort()  # Ne peut pas être instancié

    def test_conversation_service_port_is_abstract(self):
        # Arrange
        from src.domain.ports import ConversationServicePort

        # Act & Assert
        with pytest.raises(TypeError):
            ConversationServicePort()

    def test_token_service_port_is_abstract(self):
        # Arrange
        from src.domain.ports import TokenServicePort

        # Act & Assert
        with pytest.raises(TypeError):
            TokenServicePort()
