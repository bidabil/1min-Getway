# src/container.py
"""
Conteneur d'injection de dépendances amélioré
"""

from .application.use_cases import (
    CalculateTokensUseCase,
    ChatCompletionUseCase,
    ValidateApiKeyUseCase,
)
from .config import API_KEY_VALIDATION_MODE, AVAILABLE_MODELS, ONE_MIN_ASSET_API_URL
from .domain.services.chat_service import ChatService
from .infrastructure.adapters.one_min_asset_adapter import OneMinAssetAdapter
from .infrastructure.adapters.one_min_conversation_adapter import OneMinConversationAdapter
from .infrastructure.adapters.token_adapter import TiktokenAdapter


class Container:
    """
    Conteneur IoC (Inversion of Control)
    Assemble toutes les dépendances au démarrage
    """

    def __init__(self) -> None:
        # --- Infrastructure Adapters ---
        self._asset_adapter = OneMinAssetAdapter(ONE_MIN_ASSET_API_URL)
        self._conversation_adapter = OneMinConversationAdapter()
        self._token_adapter = TiktokenAdapter()

        # --- Domain Services ---
        self._chat_service = ChatService(
            asset_service=self._asset_adapter,
            conversation_service=self._conversation_adapter,
            token_service=self._token_adapter,
            available_models=AVAILABLE_MODELS,
        )

        # --- Application Use Cases ---
        self._chat_completion_use_case = ChatCompletionUseCase(self._chat_service)
        self._validate_api_key_use_case = ValidateApiKeyUseCase(
            validation_mode=API_KEY_VALIDATION_MODE
        )
        self._calculate_tokens_use_case = CalculateTokensUseCase(self._chat_service)

    # --- Getters ---
    @property
    def chat_service(self) -> ChatService:
        return self._chat_service

    @property
    def chat_completion(self) -> ChatCompletionUseCase:
        return self._chat_completion_use_case

    @property
    def validate_api_key(self) -> ValidateApiKeyUseCase:
        return self._validate_api_key_use_case

    @property
    def calculate_tokens(self) -> CalculateTokensUseCase:
        return self._calculate_tokens_use_case


# Singleton
container: Container = Container()
