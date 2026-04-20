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
        assert context.type == "UNIFY_CHAT_WITH_AI"
        assert context.prompt_object["prompt"] == "Hello"

    def test_resolve_context_creates_conversation_for_single_message(
        self, chat_service, chat_request_factory, mock_conversation_service
    ):
        request = chat_request_factory(messages=[{"role": "user", "content": "Hello"}])

        context = chat_service.resolve_context(request)

        assert context.session_id == "test-uuid-12345678"
        mock_conversation_service.create_conversation.assert_called_once()

    def test_resolve_context_reuses_session_for_multi_turn(
        self, chat_service, chat_request_factory, mock_session_store, mock_conversation_service
    ):
        mock_session_store.get.return_value = "existing-conv-id"
        request = chat_request_factory(
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
                {"role": "user", "content": "How are you?"},
            ]
        )

        context = chat_service.resolve_context(request)

        assert context.session_id == "existing-conv-id"
        mock_conversation_service.create_conversation.assert_not_called()

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

        assert context.type == "UNIFY_CHAT_WITH_AI"
        assert len(context.image_paths) == 1
        assert context.prompt_object["attachments"]["images"] == ["/uploads/test-image.png"]
        mock_asset_service.upload_image.assert_called_once()

    def test_resolve_context_pdf_with_file_ids(
        self, chat_service, chat_request_factory, mock_conversation_service
    ):
        request = chat_request_factory(
            messages=[{"role": "user", "content": "Summarize this PDF"}],
            extra_params={"file_ids": ["file-123", "file-456"]},
        )

        context = chat_service.resolve_context(request)

        assert context.type == "UNIFY_CHAT_WITH_AI"
        assert context.prompt_object["attachments"]["files"] == ["file-123", "file-456"]

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

    def test_resolve_context_handles_empty_messages(
        self,
        mock_asset_service,
        mock_conversation_service,
        mock_token_service,
        mock_session_store,
        valid_api_key,
    ):
        from src.domain.ports import ChatRequest
        from src.domain.services.chat_service import ChatService

        fresh_chat_service = ChatService(
            asset_service=mock_asset_service,
            conversation_service=mock_conversation_service,
            token_service=mock_token_service,
            session_store=mock_session_store,
            available_models=["gpt-4o"],
        )

        request = ChatRequest(
            api_key=valid_api_key,
            model="gpt-4o",
            messages=[],
            stream=False,
            extra_params=None,
        )

        context = fresh_chat_service.resolve_context(request)

        assert context.prompt_object["prompt"] == ""


class TestChatServiceSystemPromptInjection:
    """Tests pour l'injection du system prompt dans le prompt utilisateur."""

    def test_system_message_injected_at_end_of_prompt(self, chat_service, chat_request_factory):
        request = chat_request_factory(
            messages=[
                {"role": "system", "content": "Tu es un expert DevOps."},
                {"role": "user", "content": "Comment configurer nginx ?"},
            ]
        )

        context = chat_service.resolve_context(request)

        prompt = context.prompt_object["prompt"]
        assert prompt.startswith("Comment configurer nginx ?")
        assert "<system_instructions>\nTu es un expert DevOps.\n</system_instructions>" in prompt
        assert prompt.index("Comment configurer nginx ?") < prompt.index("<system_instructions>")

    def test_no_system_message_leaves_prompt_unchanged(self, chat_service, chat_request_factory):
        request = chat_request_factory(messages=[{"role": "user", "content": "Hello"}])

        context = chat_service.resolve_context(request)

        assert context.prompt_object["prompt"] == "Hello"
        assert "<system_instructions>" not in context.prompt_object["prompt"]

    def test_multiple_system_messages_are_joined(self, chat_service, chat_request_factory):
        request = chat_request_factory(
            messages=[
                {"role": "system", "content": "Tu es un expert DevOps."},
                {"role": "system", "content": "Réponds uniquement en JSON."},
                {"role": "user", "content": "Configure nginx"},
            ]
        )

        context = chat_service.resolve_context(request)

        prompt = context.prompt_object["prompt"]
        assert "Tu es un expert DevOps." in prompt
        assert "Réponds uniquement en JSON." in prompt

    def test_system_message_with_multipart_user_content(
        self, chat_service, chat_request_factory, mock_asset_service
    ):
        request = chat_request_factory(
            messages=[
                {"role": "system", "content": "Tu es un assistant visuel."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Décris cette image"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}},
                    ],
                },
            ]
        )

        context = chat_service.resolve_context(request)

        prompt = context.prompt_object["prompt"]
        assert "Décris cette image" in prompt
        assert "<system_instructions>\nTu es un assistant visuel.\n</system_instructions>" in prompt

    def test_system_message_empty_content_is_ignored(self, chat_service, chat_request_factory):
        request = chat_request_factory(
            messages=[
                {"role": "system", "content": ""},
                {"role": "user", "content": "Hello"},
            ]
        )

        context = chat_service.resolve_context(request)

        assert context.prompt_object["prompt"] == "Hello"
        assert "<system_instructions>" not in context.prompt_object["prompt"]


class TestChatServiceWebSearch:
    """Tests pour la fonctionnalité de recherche web."""

    def test_web_search_enabled(self, chat_service, chat_request_factory):
        request = chat_request_factory(
            extra_params={"web_search": True, "num_of_site": 5, "max_word": 1000}
        )

        context = chat_service.resolve_context(request)

        web_settings = context.prompt_object["settings"]["webSearchSettings"]
        assert web_settings["webSearch"] is True
        assert web_settings["numOfSite"] == 5
        assert web_settings["maxWord"] == 1000

    def test_web_search_disabled_by_default(self, chat_service, chat_request_factory):
        request = chat_request_factory()

        context = chat_service.resolve_context(request)

        web_settings = context.prompt_object["settings"]["webSearchSettings"]
        assert web_settings["webSearch"] is False

    def test_history_settings_present_by_default(self, chat_service, chat_request_factory):
        request = chat_request_factory()

        context = chat_service.resolve_context(request)

        history_settings = context.prompt_object["settings"]["historySettings"]
        assert "isMixed" in history_settings
        assert "historyMessageLimit" in history_settings

    def test_conversation_id_in_prompt_object(
        self, chat_service, chat_request_factory, mock_conversation_service
    ):
        request = chat_request_factory(messages=[{"role": "user", "content": "Hello"}])

        context = chat_service.resolve_context(request)

        assert "conversationId" in context.prompt_object
        assert context.prompt_object["conversationId"] == "test-uuid-12345678"


class TestChatServiceToolCalling:
    """Tests pour l'injection des tool definitions et la gestion des tool results."""

    def test_tools_injected_into_prompt(self, chat_service, chat_request_factory):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string", "description": "File path"}},
                        "required": ["path"],
                    },
                },
            }
        ]
        request = chat_request_factory(
            messages=[{"role": "user", "content": "List files"}],
            extra_params={"tools": tools},
        )
        context = chat_service.resolve_context(request)

        prompt = context.prompt_object["prompt"]
        assert "read_file" in prompt
        assert "<tool_call>" in prompt
        assert "path (string" in prompt
        assert "(required)" in prompt

    def test_tool_result_message_wrapped(self, chat_service, chat_request_factory):
        request = chat_request_factory(
            messages=[
                {"role": "user", "content": "List files"},
                {"role": "assistant", "content": None},
                {"role": "tool", "tool_call_id": "call_x", "content": "file1.txt\nfile2.txt"},
            ]
        )
        context = chat_service.resolve_context(request)

        prompt = context.prompt_object["prompt"]
        assert "<tool_result>" in prompt
        assert "file1.txt" in prompt

    def test_build_tools_injection_format(self):
        from src.domain.services.chat_service import ChatService

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "Content"},
                        },
                        "required": ["path", "content"],
                    },
                },
            }
        ]
        result = ChatService._build_tools_injection(tools)

        assert "write_file" in result
        assert "<tool_call>" in result
        assert "path (string, required)" in result or "path (string" in result
        assert "content (string" in result

    def test_tools_appended_to_existing_system_content(self, chat_service, chat_request_factory):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search the web",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        request = chat_request_factory(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Find something"},
            ],
            extra_params={"tools": tools},
        )
        context = chat_service.resolve_context(request)

        prompt = context.prompt_object["prompt"]
        assert "You are a helpful assistant." in prompt
        assert "search" in prompt
        assert "<tool_call>" in prompt

    def test_no_tools_no_injection(self, chat_service, chat_request_factory):
        request = chat_request_factory(messages=[{"role": "user", "content": "Hello"}])
        context = chat_service.resolve_context(request)

        prompt = context.prompt_object["prompt"]
        assert "<tool_call>" not in prompt
        assert "Tool Use Instructions" not in prompt
