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
            raw_prompt = f"[DATA_RESULT]\n{raw_prompt}\n[/DATA_RESULT]"

        # Inject tool definitions into system instructions when tools are present
        if tools := extra_params.get("tools"):
            tools_text = self._build_tools_injection(tools)
            system_content = (
                (system_content + "\n\n" + tools_text) if system_content else tools_text
            )

        if system_content:
            # Defang URLs to prevent 1min.ai from auto-crawling links found in system prompts
            safe_system = system_content.replace("https://", "hxxps://").replace(
                "http://", "hxxp://"
            )
            raw_prompt = (
                f"{raw_prompt}\n\n" f"<system_instructions>\n{safe_system}\n</system_instructions>"
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
        """Sérialise les tool definitions OpenAI en instructions XML+JSON pour le prompt.

        Les paramètres sont encodés en JSON (pas XML) pour gérer correctement
        les types complexes (arrays, objets imbriqués).
        """
        import json as _json

        lines = [
            "## Data Retrieval Protocol",
            "",
            "When the user's question requires real-time data from an external source,",
            "respond with EXACTLY this format and nothing else:",
            "",
            "FETCH: source_name",
            'PARAMS: {"key": "value"}',
            "END_FETCH",
            "",
            "When you receive a [DATA_RESULT] block, use its content to answer the user directly.",
            "Do NOT request the same data again.",
            "",
            "Available data sources:",
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
                lines.append("Parameters (JSON):")
                for pname, pinfo in properties.items():
                    req = " (required)" if pname in required_fields else ""
                    ptype = pinfo.get("type", "string")
                    pdesc = pinfo.get("description", "")
                    # Pour les arrays, afficher la structure des items
                    if ptype == "array" and "items" in pinfo:
                        items_schema = pinfo["items"]
                        lines.append(f"  - {pname} (array{req}): {pdesc}")
                        lines.append(
                            f"    Each item: {_json.dumps(items_schema, ensure_ascii=False)}"
                        )
                    elif ptype == "object" and "properties" in pinfo:
                        lines.append(f"  - {pname} (object{req}): {pdesc}")
                        lines.append(
                            f"    Shape: {_json.dumps(pinfo['properties'], ensure_ascii=False)}"
                        )
                    else:
                        lines.append(f"  - {pname} ({ptype}{req}): {pdesc}")

                # Générer un exemple concret pour les tools avec des types complexes
                example = ChatService._build_tool_example(name, properties, required_fields)
                if example:
                    lines.append("Example:")
                    lines.append(f"FETCH: {name}")
                    lines.append(f"PARAMS: {_json.dumps(example, ensure_ascii=False)}")
                    lines.append("END_FETCH")

        return "\n".join(lines)

    @staticmethod
    def _build_tool_example(
        name: str, properties: dict[str, Any], required_fields: list[str]
    ) -> dict[str, Any] | None:
        """Génère un exemple de paramètres pour un tool, utile pour les types complexes."""
        has_complex = any(pinfo.get("type") in ("array", "object") for pinfo in properties.values())
        if not has_complex:
            return None

        example: dict[str, Any] = {}
        for pname, pinfo in properties.items():
            if pname not in required_fields:
                continue
            ptype = pinfo.get("type", "string")
            if ptype == "string":
                example[pname] = f"<{pname}_value>"
            elif ptype == "array":
                items = pinfo.get("items", {})
                item_props = items.get("properties", {})
                if item_props:
                    example[pname] = [{k: f"<{k}_value>" for k in item_props}]
                else:
                    example[pname] = ["<item>"]
            elif ptype == "object":
                sub_props = pinfo.get("properties", {})
                example[pname] = {k: f"<{k}_value>" for k in sub_props}
            elif ptype == "boolean":
                example[pname] = True
            elif ptype == "integer":
                example[pname] = 0
        return example if example else None
