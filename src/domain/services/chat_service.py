import logging

from ..ports import (
    AssetServicePort,
    ChatRequest,
    ConversationContext,
    ConversationServicePort,
    TokenServicePort,
)

logger = logging.getLogger("1min-gateway.chat-service")


class ChatService:
    """
    Service de domaine pour la gestion des chats.
    Dépend uniquement des INTERFACES, pas des implémentations.
    """

    def __init__(
        self,
        asset_service: AssetServicePort,
        conversation_service: ConversationServicePort,
        token_service: TokenServicePort,
        available_models: list,
    ):
        self._asset_service = asset_service
        self._conversation_service = conversation_service
        self._token_service = token_service
        self._available_models = available_models

    def validate_model(self, model: str) -> bool:
        """Valide si le modèle est disponible"""
        return model in self._available_models

    def calculate_tokens(self, text: str, model: str) -> int:
        """Calcule les tokens pour un texte"""
        return self._token_service.calculate(text, model)

    def resolve_context(
        self,
        request: ChatRequest,
    ) -> ConversationContext | None:
        """
        Résout le contexte de conversation.
        Logique métier pure sans dépendance infrastructure.
        """
        messages = request.messages
        extra_params = request.extra_params or {}

        last_message = messages[-1] if messages else {}
        content = last_message.get("content", "")

        raw_prompt = ""
        image_paths = []

        # Extraction du contenu
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "text":
                    raw_prompt += part.get("text", "")
                elif part.get("type") == "image_url":
                    path = self._asset_service.upload_image(part, request.api_key)
                    if path:
                        image_paths.append(path)
        else:
            raw_prompt = str(content)

        # Détermination du type
        conv_type = self._determine_type(raw_prompt, image_paths, extra_params)

        # Création de conversation si nécessaire
        session_id = self._resolve_session_id(conv_type, request, extra_params, raw_prompt)

        # Construction du promptObject
        prompt_object = self._build_prompt_object(conv_type, raw_prompt, image_paths, extra_params)

        return ConversationContext(
            type=conv_type,
            session_id=session_id,
            image_paths=image_paths,
            prompt_object=prompt_object,
        )

    def _determine_type(self, prompt: str, images: list, params: dict) -> str:
        """Détermine le type de conversation"""
        import re

        if params.get("content_type") == "IMAGE_GENERATOR":
            return "IMAGE_GENERATOR"

        if params.get("file_ids"):
            return "CHAT_WITH_PDF"

        yt_pattern = r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s&]+)"
        if re.search(yt_pattern, prompt):
            return "CHAT_WITH_YOUTUBE_VIDEO"

        if images:
            return "CHAT_WITH_IMAGE"

        return "CHAT_WITH_AI"

    def _resolve_session_id(
        self, conv_type: str, request: ChatRequest, params: dict, prompt: str
    ) -> str | None:
        """Résout le session_id selon le type"""
        import re
        import uuid

        # Types sans session_id
        if conv_type in ["CHAT_WITH_AI", "CHAT_WITH_IMAGE", "IMAGE_GENERATOR"]:
            return None

        # CHAT_WITH_PDF
        if conv_type == "CHAT_WITH_PDF":
            return self._conversation_service.create_conversation(
                api_key=request.api_key,
                model=request.model,
                conv_type=conv_type,
                title=f"PDF_{request.model[:20]}_{uuid.uuid4().hex[:8]}",
                file_ids=params.get("file_ids"),
            )

        # CHAT_WITH_YOUTUBE_VIDEO
        if conv_type == "CHAT_WITH_YOUTUBE_VIDEO":
            yt_match = re.search(
                r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s&]+)", prompt
            )
            return self._conversation_service.create_conversation(
                api_key=request.api_key,
                model=request.model,
                conv_type=conv_type,
                title=f"YT_{request.model[:20]}_{uuid.uuid4().hex[:8]}",
                youtube_url=yt_match.group(1) if yt_match else None,
            )

        return None

    def _build_prompt_object(self, conv_type: str, prompt: str, images: list, params: dict) -> dict:
        """Construit le promptObject"""
        prompt_object = {
            "prompt": prompt,
            "isMixed": bool(params.get("is_mixed", False)),
            "webSearch": bool(params.get("web_search", False)),
        }

        if images and conv_type == "CHAT_WITH_IMAGE":
            prompt_object["imageList"] = images

        if prompt_object["webSearch"]:
            prompt_object["numOfSite"] = int(params.get("num_of_site", 1))
            prompt_object["maxWord"] = int(params.get("max_word", 500))

        return prompt_object
