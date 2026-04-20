import logging
import uuid
from typing import Any

from ..ports import (
    AssetServicePort,
    ChatRequest,
    ConversationContext,
    ConversationServicePort,
    SessionStorePort,
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
        session_store: SessionStorePort,
        available_models: list[str],
    ) -> None:
        self._asset_service = asset_service
        self._conversation_service = conversation_service
        self._token_service = token_service
        self._session_store = session_store
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

        system_parts = [
            m.get("content", "") for m in messages if m.get("role") == "system" and m.get("content")
        ]
        system_content = "\n".join(system_parts) if system_parts else ""

        last_message = next(
            (
                m
                for m in reversed(messages)
                if m.get("role") in ("user", "tool") and m.get("content")
            ),
            messages[-1] if messages else {},
        )
        content = last_message.get("content", "")

        raw_prompt = ""
        image_paths: list[str] = []

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

        # Wrap tool results so the model understands this is a tool execution output
        if last_message.get("role") == "tool":
            raw_prompt = f"<tool_result>\n{raw_prompt}\n</tool_result>"

        # Inject tool definitions into system instructions when tools are present
        if tools := extra_params.get("tools"):
            tools_text = self._build_tools_injection(tools)
            system_content = (
                (system_content + "\n\n" + tools_text) if system_content else tools_text
            )

        if system_content:
            raw_prompt = (
                f"{raw_prompt}\n\n"
                f"<system_instructions>\n{system_content}\n</system_instructions>"
            )

        conv_type = self._determine_type(extra_params)

        session_id = self._resolve_session_id(conv_type, request, extra_params, messages)

        prompt_object = self._build_prompt_object(raw_prompt, image_paths, extra_params, session_id)

        return ConversationContext(
            type=conv_type,
            session_id=session_id,
            image_paths=image_paths,
            prompt_object=prompt_object,
        )

    def _determine_type(self, params: dict[str, Any]) -> str:
        """Détermine le type de feature"""
        if params.get("content_type") == "IMAGE_GENERATOR":
            return "IMAGE_GENERATOR"
        return "UNIFY_CHAT_WITH_AI"

    def _resolve_session_id(
        self,
        conv_type: str,
        request: ChatRequest,
        params: dict[str, Any],
        messages: list[dict[str, Any]],
    ) -> str | None:
        """Résout le conversationId pour les chats UNIFY_CHAT_WITH_AI"""
        if conv_type == "IMAGE_GENERATOR":
            return None

        # Extraction du premier message user pour la clé de session
        first_user_content = next(
            (m.get("content", "") for m in messages if m.get("role") == "user"),
            "",
        )
        if isinstance(first_user_content, list):
            first_user_content = " ".join(
                p.get("text", "") for p in first_user_content if p.get("type") == "text"
            )

        session_key = self._session_store.make_key(
            request.api_key, request.model, str(first_user_content)
        )

        is_new_session = len(messages) <= 1

        if is_new_session:
            conv_id = self._conversation_service.create_conversation(
                api_key=request.api_key,
                model=request.model,
                conv_type="UNIFY_CHAT_WITH_AI",
                title=f"GW_{request.model[:20]}_{uuid.uuid4().hex[:8]}",
            )
            if conv_id:
                self._session_store.set(session_key, conv_id)
            return conv_id

        return self._session_store.get(session_key)

    def _build_prompt_object(
        self,
        prompt: str,
        images: list[str],
        params: dict[str, Any],
        conversation_id: str | None,
    ) -> dict[str, Any]:
        """Construit le promptObject selon la nouvelle spec Chat with AI API"""
        prompt_object: dict[str, Any] = {"prompt": prompt}

        if conversation_id:
            prompt_object["conversationId"] = conversation_id

        prompt_object["settings"] = {
            "historySettings": {
                "isMixed": bool(params.get("is_mixed", False)),
                "historyMessageLimit": int(params.get("history_message_limit", 10)),
            },
            "webSearchSettings": {
                "webSearch": bool(params.get("web_search", False)),
                "numOfSite": int(params.get("num_of_site", 3)),
                "maxWord": int(params.get("max_word", 1000)),
            },
        }

        attachments: dict[str, Any] = {}
        if images:
            attachments["images"] = images
        if params.get("file_ids"):
            attachments["files"] = params["file_ids"]
        if attachments:
            prompt_object["attachments"] = attachments

        return prompt_object

    @staticmethod
    def _build_tools_injection(tools: list[dict[str, Any]]) -> str:
        """Sérialise les tool definitions OpenAI en instructions XML pour le prompt."""
        lines = [
            "# Tool Use Instructions",
            "",
            "You have access to the following tools. When you need to call a tool, output ONLY a <tool_call> XML block — no text before or after it.",
            "",
            "Format:",
            "<tool_call>",
            "<name>tool_name</name>",
            "<parameters>",
            "<param_name>value</param_name>",
            "</parameters>",
            "</tool_call>",
            "",
            "Available tools:",
        ]

        for tool in tools:
            fn = tool.get("function", tool)
            name = fn.get("name", "")
            description = fn.get("description", "")
            params_schema = fn.get("parameters", {})
            properties = params_schema.get("properties", {})
            required_fields = params_schema.get("required", [])

            lines.append("")
            lines.append(f"### {name}")
            if description:
                lines.append(description)
            if properties:
                lines.append("Parameters:")
                for pname, pinfo in properties.items():
                    req = " (required)" if pname in required_fields else ""
                    ptype = pinfo.get("type", "string")
                    pdesc = pinfo.get("description", "")
                    lines.append(f"  - {pname} ({ptype}{req}): {pdesc}")

        return "\n".join(lines)
