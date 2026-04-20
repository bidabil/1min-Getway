# src/api/schemas.py
"""
Schémas Pydantic pour la validation des requêtes et réponses.
Documentation OpenAPI enrichie avec exemples et descriptions.
"""

from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class MessageContent(BaseModel):
    """
    Contenu d'un message (pour le multimodal).

    Supporte deux types de contenu:
    - text: Message texte simple
    - image_url: Image via URL ou base64
    """

    type: str = Field(
        ...,
        description="Type de contenu: 'text' pour du texte, 'image_url' pour une image",
        examples=["text", "image_url"],
    )
    text: str | None = Field(
        None,
        description="Texte du message (requis si type='text')",
        examples=["Hello, how can I help you?"],
    )
    image_url: dict[str, Any] | None = Field(
        None,
        description="URL de l'image (requis si type='image_url'). Format: {'url': '...'}",
        examples=[{"url": "https://example.com/image.png"}],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
            ]
        }
    }


class ChatMessage(BaseModel):
    """
    Message de chat dans une conversation.

    Les messages sont organisés par rôle:
    - system: Instructions système pour le modèle
    - user: Message de l'utilisateur
    - assistant: Réponse du modèle
    """

    role: str = Field(
        ...,
        description="Rôle de l'auteur du message: 'system', 'user', ou 'assistant'",
        examples=["user", "assistant", "system"],
    )
    content: str | list[MessageContent] | None = Field(
        None,
        description="Contenu du message. Peut être une chaîne, une liste de contenus (multimodal), ou null pour les messages assistant avec tool_calls",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "https://example.com/image.png"},
                        },
                    ],
                },
            ]
        }
    }


class ChatCompletionRequest(BaseModel):
    """
    Requête de chat completion au format OpenAI.

    Cette API traduit les requêtes OpenAI vers le format 1min.ai.
    Supporte le streaming, les images, et les fichiers PDF.
    """

    model: str = Field(
        default="gpt-4o-mini",
        description="Modèle à utiliser. Options: gpt-4o, gpt-4o-mini, claude-3-haiku, mistral-medium-latest",
        examples=["gpt-4o", "gpt-4o-mini", "claude-3-haiku"],
    )
    messages: list[ChatMessage] = Field(
        ..., description="Liste des messages de la conversation", min_length=1
    )
    stream: bool = Field(default=False, description="Activer le streaming Server-Sent Events (SSE)")
    temperature: float | None = Field(
        None,
        ge=0,
        le=2,
        description="Température d'échantillonnage (0-2). Plus élevé = plus créatif",
        examples=[0.7, 1.0],
    )
    max_tokens: int | None = Field(
        None, ge=1, description="Nombre maximum de tokens à générer", examples=[1000, 2000]
    )
    top_p: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Nucleus sampling (0-1). Alternative à temperature",
        examples=[0.9, 1.0],
    )

    # Paramètres supplémentaires pour 1min.ai
    web_search: bool | None = Field(
        None, description="Activer la recherche web pour enrichir les réponses"
    )
    file_ids: list[str] | None = Field(
        None,
        description="IDs de fichiers PDF précédemment uploadés pour analyse",
        examples=[["file-abc123", "file-def456"]],
    )

    # Function calling (tool use)
    tools: list[dict[str, Any]] | None = Field(
        None,
        description="Liste des outils disponibles pour le function calling (format OpenAI)",
    )
    tool_choice: str | dict[str, Any] | None = Field(
        None,
        description="Contrôle la sélection d'outil: 'auto', 'none', ou {'type': 'function', 'function': {'name': '...'}}",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hello!"},
                    ],
                    "stream": False,
                    "temperature": 0.7,
                },
                {
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "Analyze this document"}],
                    "file_ids": ["file-abc123"],
                    "web_search": True,
                },
            ]
        }
    }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class ChatCompletionChoice(BaseModel):
    """Choix de completion dans la réponse."""

    index: int = Field(description="Index du choix")
    message: dict[str, str] = Field(
        description="Message généré",
        examples=[{"role": "assistant", "content": "Hello! How can I help you today?"}],
    )
    finish_reason: str = Field(
        description="Raison de fin: 'stop', 'length', 'content_filter'", examples=["stop"]
    )


class UsageInfo(BaseModel):
    """Informations d'utilisation des tokens."""

    prompt_tokens: int = Field(description="Tokens dans la requête")
    completion_tokens: int = Field(description="Tokens dans la réponse")
    total_tokens: int = Field(description="Total des tokens")


class ChatCompletionResponse(BaseModel):
    """
    Réponse de chat completion au format OpenAI.

    Contient le message généré, les informations d'utilisation,
    et les métadonnées de la requête.
    """

    id: str = Field(description="Identifiant unique de la completion", examples=["chatcmpl-abc123"])
    object: str = Field(default="chat.completion", description="Type d'objet")
    created: int = Field(description="Timestamp Unix de création")
    model: str = Field(description="Modèle utilisé", examples=["gpt-4o-mini"])
    choices: list[ChatCompletionChoice] = Field(description="Liste des choix de completion")
    usage: UsageInfo = Field(description="Informations d'utilisation des tokens")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "chatcmpl-abc123",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Hello! How can I help you?"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            }
        }
    }


class ModelInfo(BaseModel):
    """Information sur un modèle disponible."""

    id: str = Field(
        description="Identifiant du modèle", examples=["gpt-4o", "gpt-4o-mini", "claude-3-haiku"]
    )
    object: str = Field(default="model", description="Type d'objet")
    created: int = Field(default=1700000000, description="Timestamp de création")
    owned_by: str = Field(default="1min-ai", description="Propriétaire du modèle")


class ModelsResponse(BaseModel):
    """Réponse de l'endpoint /v1/models listant les modèles disponibles."""

    object: str = Field(default="list", description="Type d'objet")
    data: list[ModelInfo] = Field(description="Liste des modèles disponibles")

    model_config = {
        "json_schema_extra": {
            "example": {
                "object": "list",
                "data": [
                    {
                        "id": "gpt-4o",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "1min-ai",
                    },
                    {
                        "id": "gpt-4o-mini",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "1min-ai",
                    },
                ],
            }
        }
    }


class ErrorResponse(BaseModel):
    """
    Réponse d'erreur standardisée.

    Suit le format d'erreur OpenAI avec un code et un message.
    """

    success: bool = Field(default=False, description="Toujours false pour les erreurs")
    error: dict[str, str] = Field(description="Détails de l'erreur avec 'code' et 'message'")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": False,
                    "error": {"code": "UNAUTHORIZED", "message": "API key is required"},
                },
                {
                    "success": False,
                    "error": {"code": "MODEL_NOT_FOUND", "message": "Model 'invalid' not found"},
                },
            ]
        }
    }


class HealthResponse(BaseModel):
    """Réponse de l'endpoint de santé basique."""

    status: str = Field(description="Statut: 'ok' ou 'error'", examples=["ok"])
    architecture: str = Field(
        description="Architecture technique", examples=["FastAPI + Clean Architecture"]
    )
    circuit_breaker: dict[str, Any] = Field(description="État du circuit breaker")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
                "architecture": "FastAPI + Clean Architecture",
                "circuit_breaker": {"state": "CLOSED", "failures": 0},
            }
        }
    }


class CircuitBreakerStats(BaseModel):
    """Statistiques détaillées du circuit breaker."""

    name: str = Field(description="Nom du circuit breaker")
    state: str = Field(
        description="État actuel: CLOSED, OPEN, HALF_OPEN", examples=["CLOSED", "OPEN", "HALF_OPEN"]
    )
    failure_count: int = Field(description="Nombre actuel d'échecs")
    failure_threshold: int = Field(description="Seuil d'échecs pour ouverture")
    recovery_timeout: int = Field(description="Délai de récupération en secondes")
    metrics: dict[str, int] = Field(
        description="Métriques: total_calls, successes, failures, rejected_calls"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "api_circuit_breaker",
                "state": "CLOSED",
                "failure_count": 0,
                "failure_threshold": 3,
                "recovery_timeout": 60,
                "metrics": {
                    "total_calls": 100,
                    "successes": 98,
                    "failures": 2,
                    "rejected_calls": 0,
                },
            }
        }
    }
