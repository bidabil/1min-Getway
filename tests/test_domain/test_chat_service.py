# tests/test_domain/test_chat_service.py
"""
Tests pour le ChatService (Domain Layer).
Utilise le pattern AAA: Arrange, Act, Assert.
"""

import pytest


class TestChatServiceModelValidation:
    """Tests pour la validation des modèles."""

    def test_validate_model_returns_true_for_available_model(self, chat_service):
        model = "gpt-4o"
        result = chat_service.validate_model(model)
        assert result is True

    def test_validate_model_returns_false_for_unknown_model(self, chat_service):
        model = "unknown-model-xyz"
        result = chat_service.validate_model(model)
        assert result is False

    @pytest.mark.parametrize(
        "model,expected",
        [
            ("gpt-4o", True),
            ("gpt-4o-mini", True),
            ("claude-3-haiku", True),
            ("mistral-medium-latest", True),
            ("invalid-model", False),
            ("", False),
        ],
    )
    def test_validate_model_parametrized(self, chat_service, model, expected):
        result = chat_service.validate_model(model)
        assert result == expected


class TestChatServiceTokenCalculation:
    """Tests pour le calcul de tokens."""

    def test_calculate_tokens_delegates_to_token_service(self, chat_service, mock_token_service):
        text = "Hello world"
        model = "gpt-4o"
        mock_token_service.calculate.return_value = 2

        result = chat_service.calculate_tokens(text, model)

        assert result == 2
        mock_token_service.calculate.assert_called_once_with(text, model)

    def test_calculate_tokens_with_empty_string(self, chat_service, mock_token_service):
        mock_token_service.calculate.return_value = 0
        result = chat_service.calculate_tokens("", "gpt-4o")
        assert result == 0


class TestChatServiceContextResolution:
    """Tests pour la résolution de contexte."""

    def test_resolve_context_simple_chat(self, chat_service, chat_request_factory):
        request = chat_request_factory(messages=[{"role": "user", "content": "Hello"}])

        context = chat_service.resolve_context(request)

        assert context is not None
        assert context.type == "CHAT_WITH_AI"
        assert context.session_id is None
        assert context.prompt_object["prompt"] == "Hello"

    def test_resolve_context_with_image(
        self, chat_service, chat_request_factory, mock_asset_service
    ):
        request = chat_request_factory(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}},
                    ],
                }
            ]
        )

        context = chat_service.resolve_context(request)

        assert context.type == "CHAT_WITH_IMAGE"
        assert len(context.image_paths) == 1
        mock_asset_service.upload_image.assert_called_once()

    def test_resolve_context_youtube_detection(
        self, chat_service, chat_request_factory, mock_conversation_service, youtube_url
    ):
        request = chat_request_factory(
            messages=[{"role": "user", "content": f"Summarize {youtube_url}"}]
        )

        context = chat_service.resolve_context(request)

        assert context.type == "CHAT_WITH_YOUTUBE_VIDEO"
        assert context.session_id is not None
        mock_conversation_service.create_conversation.assert_called_once()

    def test_resolve_context_pdf_with_file_ids(
        self, chat_service, chat_request_factory, mock_conversation_service
    ):
        request = chat_request_factory(
            messages=[{"role": "user", "content": "Summarize this PDF"}],
            extra_params={"file_ids": ["file-123", "file-456"]},
        )

        context = chat_service.resolve_context(request)

        assert context.type == "CHAT_WITH_PDF"
        assert context.session_id is not None
        mock_conversation_service.create_conversation.assert_called_once()

    def test_resolve_context_extracts_text_from_multipart(self, chat_service, chat_request_factory):
        request = chat_request_factory(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello "},
                        {"type": "text", "text": "world"},
                    ],
                }
            ]
        )

        context = chat_service.resolve_context(request)

        assert "Hello" in context.prompt_object["prompt"]
        assert "world" in context.prompt_object["prompt"]

    # CORRECTION: Créer un nouveau ChatService et ChatRequest pour ce test spécifique
    def test_resolve_context_handles_empty_messages(
        self, mock_asset_service, mock_conversation_service, mock_token_service, valid_api_key
    ):
        # Arrange - Créer un ChatService frais
        from src.domain.ports import ChatRequest
        from src.domain.services.chat_service import ChatService

        fresh_chat_service = ChatService(
            asset_service=mock_asset_service,
            conversation_service=mock_conversation_service,
            token_service=mock_token_service,
            available_models=["gpt-4o"],
        )

        request = ChatRequest(
            api_key=valid_api_key,
            model="gpt-4o",
            messages=[],  # Liste vide explicite
            stream=False,
            extra_params=None,
        )

        # Act
        context = fresh_chat_service.resolve_context(request)

        # Assert
        assert context.prompt_object["prompt"] == ""


class TestChatServiceWebSearch:
    """Tests pour la fonctionnalité de recherche web."""

    def test_web_search_enabled(self, chat_service, chat_request_factory):
        request = chat_request_factory(
            extra_params={"web_search": True, "num_of_site": 5, "max_word": 1000}
        )

        context = chat_service.resolve_context(request)

        assert context.prompt_object["webSearch"] is True
        assert context.prompt_object["numOfSite"] == 5
        assert context.prompt_object["maxWord"] == 1000

    def test_web_search_disabled_by_default(self, chat_service, chat_request_factory):
        request = chat_request_factory()

        context = chat_service.resolve_context(request)

        assert context.prompt_object["webSearch"] is False
        assert "numOfSite" not in context.prompt_object
