# ============================================================================
# src/domain/ports.py - INTERFACES (Contrats)
# ============================================================================
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationContext:
    """Value Object représentant le contexte de conversation"""

    type: str
    session_id: str | None
    image_paths: list[str]
    prompt_object: dict[str, Any]


@dataclass
class ChatRequest:
    """Value Object pour une requête de chat"""

    api_key: str
    model: str
    messages: list[dict[str, Any]]
    stream: bool = False
    extra_params: dict[str, Any] = field(default_factory=dict)


class AssetServicePort(ABC):
    """Interface pour le service d'assets"""

    @abstractmethod
    def upload_image(self, image_data: dict[str, Any], api_key: str) -> str | None:
        """Upload une image et retourne son chemin"""
        pass


class ConversationServicePort(ABC):
    """Interface pour le service de conversation"""

    @abstractmethod
    def create_conversation(
        self,
        api_key: str,
        model: str,
        conv_type: str,
        title: str,
        file_ids: list[str] | None = None,
        youtube_url: str | None = None,
    ) -> str | None:
        """Crée une conversation et retourne son UUID"""
        pass


class AIFeatureServicePort(ABC):
    """Interface pour le service AI Feature"""

    @abstractmethod
    def call_feature(
        self,
        api_key: str,
        payload: dict[str, Any],
        stream: bool = False,
    ) -> Any:
        """Appelle l'API AI Feature"""
        pass


class SessionStorePort(ABC):
    """Interface pour le store de sessions (conversationId par session)"""

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Retourne le conversationId associé à la clé, ou None"""
        pass

    @abstractmethod
    def set(self, key: str, conversation_id: str) -> None:
        """Stocke un conversationId pour la clé donnée"""
        pass

    @abstractmethod
    def make_key(self, api_key: str, model: str, first_user_message: str) -> str:
        """Construit une clé de session déterministe"""
        pass


class TokenServicePort(ABC):
    """Interface pour le calcul de tokens"""

    @abstractmethod
    def calculate(self, text: str, model: str) -> int:
        """Calcule le nombre de tokens"""
        pass
