# ============================================================================
# src/infrastructure/adapters/one_min_conversation_adapter.py
# ============================================================================

from ...domain.ports import ConversationServicePort


class OneMinConversationAdapter(ConversationServicePort):
    """Implémentation du service de conversation pour 1min.ai"""

    def create_conversation(
        self,
        api_key: str,
        model: str,
        conv_type: str = "UNIFY_CHAT_WITH_AI",
        title: str = "Gateway Session",
        file_ids: list[str] | None = None,
        youtube_url: str | None = None,
    ) -> str | None:
        from ..one_min_client import create_1min_conversation

        return create_1min_conversation(
            api_key=api_key,
            model=model,
            conv_type=conv_type,
            title=title,
            file_ids=file_ids,
            youtube_url=youtube_url,
        )
