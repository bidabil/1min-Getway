# src/application/use_cases.py
"""
Application Layer - Use Cases
Chaque use case = une action utilisateur
"""

from dataclasses import dataclass
from typing import Any, Union

from ..domain.ports import ChatRequest
from ..domain.services.chat_service import ChatService


# ============================================================================
# RESULT PATTERN - Pas d'exceptions pour le flux métier
# ============================================================================
@dataclass
class Success:
    """Résultat réussi"""

    data: Any


@dataclass
class Failure:
    """Résultat en erreur"""

    error_code: str
    message: str


Result = Union[Success, Failure]


# ============================================================================
# USE CASE: Chat Completion
# ============================================================================
class ChatCompletionUseCase:
    """
    Use Case : Exécuter une completion de chat

    Responsabilités :
    - Validation des entrées
    - Orchestration du flux
    - Gestion des erreurs métier
    """

    def __init__(self, chat_service: ChatService) -> None:
        self._chat_service = chat_service

    def execute(self, request: ChatRequest) -> Result:
        """
        Exécute le use case de chat completion.

        Returns:
            Success(ConversationContext) ou Failure(error)
        """
        # 1. Validation du modèle
        if not self._chat_service.validate_model(request.model):
            return Failure(
                error_code="MODEL_NOT_FOUND", message=f"Model '{request.model}' is not available"
            )

        # 2. Validation des messages
        if not request.messages:
            return Failure(error_code="INVALID_REQUEST", message="No messages provided")

        last_user_message = next(
            (
                m
                for m in reversed(request.messages)
                if m.get("role") in ("user", "tool") and m.get("content")
            ),
            None,
        )
        if not last_user_message:
            return Failure(
                error_code="INVALID_REQUEST", message="No user message with content found"
            )

        # 3. Résolution du contexte
        try:
            context = self._chat_service.resolve_context(request)

            if context is None:
                return Failure(
                    error_code="CONTEXT_ERROR", message="Failed to resolve conversation context"
                )

            return Success(data=context)

        except Exception as e:
            return Failure(error_code="INTERNAL_ERROR", message=str(e))


# ============================================================================
# USE CASE: Validate API Key
# ============================================================================
class ValidateApiKeyUseCase:
    """
    Use Case : Valider une clé API

    Validation en deux étapes:
    1. Validation du format (rapide)
    2. Validation auprès de l'API 1min.ai (optionnel, configurable)
    """

    # Mode validation: "fast" (format only) ou "full" (avec appel API)
    VALIDATION_MODE = "fast"  # Par défaut, validation rapide uniquement

    def __init__(self, validation_mode: str = "fast") -> None:
        self._validation_mode = validation_mode

    def execute(self, api_key: str) -> Result:
        # Validation du format (toujours effectuée)
        if not api_key:
            return Failure(error_code="UNAUTHORIZED", message="Missing API key")

        if len(api_key) < 32:
            return Failure(error_code="UNAUTHORIZED", message="Invalid API key format (too short)")

        if len(api_key) > 128:
            return Failure(error_code="UNAUTHORIZED", message="Invalid API key format (too long)")

        # Validation complète si configurée
        if self._validation_mode == "full":
            from ..infrastructure.api_key_validator import api_key_validator

            is_valid, error_msg = api_key_validator.validate(api_key)
            if not is_valid:
                return Failure(error_code="UNAUTHORIZED", message=error_msg or "Invalid API key")

        return Success(data=api_key)


# ============================================================================
# USE CASE: Calculate Tokens
# ============================================================================
class CalculateTokensUseCase:
    """Use Case : Calculer les tokens"""

    def __init__(self, chat_service: ChatService) -> None:
        self._chat_service = chat_service

    def execute(self, text: str, model: str) -> Result:
        try:
            tokens = self._chat_service.calculate_tokens(text, model)
            return Success(data=tokens)
        except Exception as e:
            return Failure(error_code="TOKEN_ERROR", message=str(e))
