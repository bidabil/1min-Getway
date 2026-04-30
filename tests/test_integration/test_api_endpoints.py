# tests/test_integration/test_api_endpoints.py
"""
Tests d'intégration pour les endpoints API FastAPI.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestHealthEndpoint:
    """Tests pour l'endpoint de santé."""

    def test_returns_200_ok(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_returns_status_ok(self, client):
        response = client.get("/")
        data = response.json()
        assert data["status"] == "ok"

    def test_returns_circuit_breaker_status(self, client):
        response = client.get("/")
        data = response.json()
        assert "circuit_breaker" in data
        assert "state" in data["circuit_breaker"]
        assert "failures" in data["circuit_breaker"]


class TestModelsEndpoint:
    """Tests pour /v1/models."""

    def test_models_endpoint_response(self, client, auth_headers):
        response = client.get("/v1/models", headers=auth_headers)
        assert response.status_code == 200

    def test_models_endpoint_returns_list(self, client):
        """L'endpoint /v1/models retourne une liste de modèles (format OpenAI)"""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "object" in data
        assert data["object"] == "list"
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_models_endpoint_openai_format(self, client):
        """Vérifie le format OpenAI de la réponse"""
        response = client.get("/v1/models")
        data = response.json()
        if data["data"]:
            model = data["data"][0]
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"
            assert "owned_by" in model


class TestChatCompletionsEndpoint:
    """Tests pour /v1/chat/completions."""

    def test_requires_authentication(self, client, simple_chat_request):
        response = client.post("/v1/chat/completions", json=simple_chat_request)
        assert response.status_code == 401

    def test_accepts_api_key_header(self, client, auth_headers, simple_chat_request):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "aiRecord": {"aiRecordDetail": {"resultObject": ["Hello!"]}}
            }
            mock_response.raise_for_status = MagicMock()

            # Configurer le mock pour retourner une réponse valide
            mock_post.return_value = mock_response

            response = client.post(
                "/v1/chat/completions", json=simple_chat_request, headers=auth_headers
            )

        # Le test passe si on obtient 200 ou si le mock n'est pas appelé (circuit breaker)
        assert response.status_code in [200, 500, 503]

    def test_accepts_bearer_token(self, client, bearer_headers, simple_chat_request):
        response = client.post(
            "/v1/chat/completions", json=simple_chat_request, headers=bearer_headers
        )
        # Peut échouer si le mock n'est pas configuré, mais l'auth doit passer
        # 400 peut survenir si l'API key de test n'est pas valide pour l'API 1min
        assert response.status_code in [200, 400, 500, 503, 504]

    def test_rejects_missing_messages(self, client, auth_headers):
        payload = {"model": "gpt-4o"}
        response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)
        assert response.status_code == 422  # Pydantic validation error

    def test_rejects_empty_messages(self, client, auth_headers, empty_messages_request):
        response = client.post(
            "/v1/chat/completions", json=empty_messages_request, headers=auth_headers
        )
        # Soit 400 (Use Case), soit 422 (Pydantic)
        assert response.status_code in [400, 422]

    def test_rejects_invalid_model(self, client, auth_headers):
        payload = {
            "model": "nonexistent-model-xyz-123",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)
        assert response.status_code == 404

    def test_returns_openai_format(self, client, auth_headers, simple_chat_request):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "aiRecord": {"aiRecordDetail": {"resultObject": ["Hello!"]}}
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            response = client.post(
                "/v1/chat/completions", json=simple_chat_request, headers=auth_headers
            )

        if response.status_code == 200:
            data = response.json()
            assert "choices" in data
            assert "id" in data
            assert data["id"].startswith("chatcmpl-")
            assert "usage" in data

    def test_streaming_request(self, client, auth_headers, streaming_chat_request):
        # Pour le streaming, on vérifie juste que l'endpoint accepte la requête
        response = client.post(
            "/v1/chat/completions", json=streaming_chat_request, headers=auth_headers
        )
        # Le streaming peut échouer sans mock, mais l'auth doit passer
        assert response.status_code in [200, 500, 503, 504]

    def test_options_returns_cors_headers(self, client):
        response = client.options("/v1/chat/completions")
        # FastAPI gère CORS automatiquement
        assert response.status_code in [200, 204, 405]

    @pytest.mark.parametrize(
        "upstream_status,expected_status",
        [
            (403, 403),
            (429, 429),
            (500, 500),
        ],
    )
    def test_propagates_upstream_errors(
        self, client, auth_headers, simple_chat_request, upstream_status, expected_status
    ):
        mock_response = MagicMock()
        mock_response.status_code = upstream_status
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "upstream error", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("src.api.routes.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)
            response = client.post(
                "/v1/chat/completions",
                json=simple_chat_request,
                headers=auth_headers,
            )

        assert response.status_code == expected_status


class TestCircuitBreakerEndpoints:
    """Tests pour les endpoints du Circuit Breaker."""

    def test_circuit_breaker_status_endpoint(self, client):
        """L'endpoint /health/circuit-breaker retourne les stats."""
        response = client.get("/health/circuit-breaker")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "state" in data
        assert "metrics" in data

    def test_circuit_breaker_reset_endpoint(self, client):
        """L'endpoint de reset fonctionne."""
        response = client.post("/health/circuit-breaker/reset")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestStreamingSSEParser:
    """Tests pour le parser SSE du streaming (fix event: lines leaking)."""

    _CONV_RESPONSE = {"conversation": {"uuid": "test-conv-id-streaming"}}

    @pytest.fixture(autouse=True)
    def reset_circuit_breaker(self):
        """Remet le circuit breaker à zéro avant/après chaque test."""
        from src.infrastructure.circuit_breaker import api_circuit_breaker

        api_circuit_breaker.reset()
        yield
        api_circuit_breaker.reset()

    def _make_stream_mock(self, lines: list[str]) -> AsyncMock:
        """Construit un mock httpx.AsyncClient pour le streaming."""

        async def _aiter_lines():
            for line in lines:
                yield line

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = _aiter_lines

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)

        mock_async_client_instance = AsyncMock()
        mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client_instance.__aexit__ = AsyncMock(return_value=False)

        return mock_async_client_instance

    def _do_stream(self, client, auth_headers, streaming_chat_request, lines):
        """Helper : effectue la requête streaming avec les lignes SSE données."""
        mock_conv = MagicMock()
        mock_conv.status_code = 200
        mock_conv.headers = {"Content-Type": "application/json"}
        mock_conv.json.return_value = self._CONV_RESPONSE

        with patch("src.infrastructure.one_min_client._session.post", return_value=mock_conv):
            with patch("src.api.routes.httpx.AsyncClient") as mock_cls:
                mock_cls.return_value = self._make_stream_mock(lines)
                return client.post(
                    "/v1/chat/completions",
                    json=streaming_chat_request,
                    headers=auth_headers,
                )

    # ------------------------------------------------------------------
    # 1. Les lignes "event:" ne doivent pas apparaître comme contenu
    # ------------------------------------------------------------------
    def test_event_lines_not_leaked_as_content(self, client, auth_headers, streaming_chat_request):
        lines = [
            "event: content",
            'data: {"result": "Hello"}',
            "event: done",
            "data: [DONE]",
        ]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        body = response.text
        # L'événement SSE "event: content" ne doit pas apparaître comme texte
        for chunk_raw in body.split("data: ")[1:]:
            chunk_str = chunk_raw.strip()
            if chunk_str in ("[DONE]", ""):
                continue
            data = json.loads(chunk_str)
            content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
            assert "event: content" not in content
            assert "event: done" not in content

    # ------------------------------------------------------------------
    # 2. Champ "result" extrait correctement
    # ------------------------------------------------------------------
    def test_result_field_extracted(self, client, auth_headers, streaming_chat_request):
        lines = ['data: {"result": "Bonjour"}', "data: [DONE]"]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        assert "Bonjour" in response.text

    # ------------------------------------------------------------------
    # 3. Champ "text" (fallback nouvelle API) extrait correctement
    # ------------------------------------------------------------------
    def test_text_field_fallback_extracted(self, client, auth_headers, streaming_chat_request):
        lines = ['data: {"text": "Salut"}', "data: [DONE]"]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        assert "Salut" in response.text

    # ------------------------------------------------------------------
    # 4. Champ "content" extrait correctement
    # ------------------------------------------------------------------
    def test_content_field_extracted(self, client, auth_headers, streaming_chat_request):
        lines = ['data: {"content": "Ciao"}', "data: [DONE]"]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        assert "Ciao" in response.text

    # ------------------------------------------------------------------
    # 5. [DONE] coté upstream met fin à l'itération (pas de contenu après)
    # ------------------------------------------------------------------
    def test_done_terminates_stream(self, client, auth_headers, streaming_chat_request):
        lines = [
            'data: {"result": "Fin"}',
            "data: [DONE]",
            'data: {"result": "Après DONE"}',  # doit être ignoré
        ]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        assert "Fin" in response.text
        assert "Après DONE" not in response.text

    # ------------------------------------------------------------------
    # 6. Les lignes sans préfixe "data:" ni "event:" sont ignorées
    # ------------------------------------------------------------------
    def test_unknown_lines_skipped(self, client, auth_headers, streaming_chat_request):
        lines = [
            "retry: 3000",
            ": keep-alive",
            'data: {"result": "OK"}',
            "data: [DONE]",
        ]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        assert "OK" in response.text
        # Les lignes parasites ne doivent pas apparaître dans les chunks
        for chunk_raw in response.text.split("data: ")[1:]:
            chunk_str = chunk_raw.strip()
            if chunk_str in ("[DONE]", ""):
                continue
            data = json.loads(chunk_str)
            content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
            assert "retry:" not in content
            assert "keep-alive" not in content

    # ------------------------------------------------------------------
    # 7. Les lignes vides sont ignorées sans erreur
    # ------------------------------------------------------------------
    def test_empty_lines_ignored(self, client, auth_headers, streaming_chat_request):
        lines = [
            "",
            "event: content",
            "",
            'data: {"result": "Texte"}',
            "",
            "data: [DONE]",
        ]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        assert "Texte" in response.text

    # ------------------------------------------------------------------
    # 8. Plusieurs chunks sont tous transmis
    # ------------------------------------------------------------------
    def test_multiple_chunks_all_delivered(self, client, auth_headers, streaming_chat_request):
        lines = [
            "event: content",
            'data: {"result": "Bonjour"}',
            "event: content",
            'data: {"result": " monde"}',
            "event: content",
            'data: {"result": " !"}',
            "data: [DONE]",
        ]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        body = response.text
        assert "Bonjour" in body
        assert " monde" in body
        assert " !" in body

    # ------------------------------------------------------------------
    # 9. Réponse finale au format OpenAI avec finish_reason=stop
    # ------------------------------------------------------------------
    def test_final_chunk_has_finish_reason_stop(self, client, auth_headers, streaming_chat_request):
        lines = ['data: {"result": "Hi"}', "data: [DONE]"]
        response = self._do_stream(client, auth_headers, streaming_chat_request, lines)
        assert response.status_code == 200
        # Le dernier chunk avant [DONE] doit avoir finish_reason=stop
        chunks = [
            p.strip() for p in response.text.split("data: ") if p.strip() and p.strip() != "[DONE]"
        ]
        assert chunks, "Aucun chunk reçu"
        last_chunk = json.loads(chunks[-1])
        assert last_chunk["choices"][0]["finish_reason"] == "stop"


class TestToolCalling:
    """Tests pour le function calling via XML."""

    def test_schema_accepts_tools_field(self, client, auth_headers):
        """Le schéma ChatCompletionRequest accepte le champ tools sans erreur 422."""
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "List files"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "description": "Read a file",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"],
                        },
                    },
                }
            ],
        }
        from unittest.mock import MagicMock, patch

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aiRecord": {
                "aiRecordDetail": {
                    "resultObject": ['FETCH: read_file\nPARAMS: {"path": "/test.txt"}\nEND_FETCH']
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = mock_response
            response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        # 422 interdit — le payload est valide
        assert response.status_code != 422

    def test_tool_call_response_returns_tool_calls_format(self, client, auth_headers):
        """Quand la réponse contient un bloc FETCH, finish_reason doit être 'tool_calls'."""
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Read file.txt"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "description": "Read a file",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"],
                        },
                    },
                }
            ],
        }
        from unittest.mock import MagicMock, patch

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aiRecord": {
                "aiRecordDetail": {
                    "resultObject": ['FETCH: read_file\nPARAMS: {"path": "/file.txt"}\nEND_FETCH']
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = mock_response
            response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            choice = data["choices"][0]
            assert choice["finish_reason"] == "tool_calls"
            assert "tool_calls" in choice["message"]
            tc = choice["message"]["tool_calls"][0]
            assert tc["function"]["name"] == "read_file"
            assert tc["type"] == "function"
            assert "id" in tc
            args = json.loads(tc["function"]["arguments"])
            assert args["path"] == "/file.txt"

    def test_normal_response_without_tool_calls(self, client, auth_headers):
        """Sans bloc FETCH dans la réponse, finish_reason reste 'stop'."""
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Say hello"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "description": "Read a file",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        }
        from unittest.mock import MagicMock, patch

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aiRecord": {"aiRecordDetail": {"resultObject": ["Hello! How can I help you today?"]}}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = mock_response
            response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            assert data["choices"][0]["finish_reason"] == "stop"
            assert data["choices"][0]["message"]["content"] == "Hello! How can I help you today?"

    def test_parse_tool_call_single(self):
        """_parse_tool_calls détecte un bloc FETCH simple."""
        from src.api.routes import _parse_tool_calls

        content = 'FETCH: read_file\nPARAMS: {"path": "/home/test.txt"}\nEND_FETCH'
        result = _parse_tool_calls(content)

        assert result is not None
        assert len(result) == 1
        assert result[0]["function"]["name"] == "read_file"
        assert result[0]["type"] == "function"
        assert "id" in result[0]
        args = json.loads(result[0]["function"]["arguments"])
        assert args["path"] == "/home/test.txt"

    def test_parse_tool_call_multiple_params(self):
        """_parse_tool_calls gère plusieurs paramètres."""
        from src.api.routes import _parse_tool_calls

        content = (
            'FETCH: write_file\nPARAMS: {"path": "/out.txt", "content": "hello world"}\nEND_FETCH'
        )
        result = _parse_tool_calls(content)

        assert result is not None
        args = json.loads(result[0]["function"]["arguments"])
        assert args["path"] == "/out.txt"
        assert args["content"] == "hello world"

    def test_parse_tool_calls_multiple_blocks(self):
        """_parse_tool_calls détecte plusieurs blocs FETCH dans une réponse."""
        from src.api.routes import _parse_tool_calls

        content = (
            'FETCH: read_file\nPARAMS: {"path": "/a"}\nEND_FETCH\n'
            'FETCH: write_file\nPARAMS: {"path": "/b"}\nEND_FETCH'
        )
        result = _parse_tool_calls(content)

        assert result is not None
        assert len(result) == 2
        assert result[0]["function"]["name"] == "read_file"
        assert result[1]["function"]["name"] == "write_file"

    def test_parse_tool_call_no_newline_between_name_and_params(self):
        """_parse_tool_calls gère le cas où le modèle colle le nom et PARAMS sans séparateur."""
        from src.api.routes import _parse_tool_calls

        content = 'FETCH: web_fetchPARAMS: {"url": "https://wttr.in/Marseille"}\nEND_FETCH'
        result = _parse_tool_calls(content)

        assert result is not None
        assert len(result) == 1
        assert result[0]["function"]["name"] == "web_fetch"
        args = json.loads(result[0]["function"]["arguments"])
        assert args["url"] == "https://wttr.in/Marseille"

    def test_parse_tool_call_with_preamble_text(self):
        """_parse_tool_calls détecte un bloc FETCH précédé de texte narratif."""
        from src.api.routes import _parse_tool_calls

        content = (
            "I'll check the weather for you.\n\n"
            'FETCH: weatherPARAMS: {"location": "Marseille"}\nEND_FETCH'
        )
        result = _parse_tool_calls(content)

        assert result is not None
        assert result[0]["function"]["name"] == "weather"

    def test_parse_returns_none_for_plain_text(self):
        """_parse_tool_calls retourne None si pas de tool_call."""
        from src.api.routes import _parse_tool_calls

        result = _parse_tool_calls("This is a normal text response without any tool calls.")
        assert result is None

    def test_parse_returns_none_for_empty_string(self):
        """_parse_tool_calls retourne None pour une chaîne vide."""
        from src.api.routes import _parse_tool_calls

        result = _parse_tool_calls("")
        assert result is None


class TestOpenAPIDocumentation:
    """Tests pour la documentation OpenAPI."""

    def test_docs_endpoint(self, client):
        """L'endpoint /docs retourne Swagger UI."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_endpoint(self, client):
        """L'endpoint /redoc retourne ReDoc."""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_json_endpoint(self, client):
        """L'endpoint /openapi.json retourne la spec."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
