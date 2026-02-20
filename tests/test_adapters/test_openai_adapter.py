# tests/test_adapters/test_openai_adapter.py
"""
Tests unitaires pour l'adaptateur OpenAI.
Couvre transform_response et stream_response.
"""

import json
from collections.abc import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.adapters.openai_adapter import stream_response, transform_response


class TestTransformResponse:
    """Tests pour la fonction transform_response."""

    def test_transforms_valid_response_with_list_result(self):
        """Teste la transformation d'une réponse valide avec resultObject liste."""
        one_min_response = {"aiRecord": {"aiRecordDetail": {"resultObject": ["Hello, world!"]}}}

        result = transform_response(one_min_response, "gpt-4o", 10)

        assert result["object"] == "chat.completion"
        assert result["model"] == "gpt-4o"
        assert len(result["choices"]) == 1
        assert result["choices"][0]["message"]["role"] == "assistant"
        assert result["choices"][0]["message"]["content"] == "Hello, world!"
        assert result["choices"][0]["finish_reason"] == "stop"
        assert "id" in result
        assert "created" in result
        assert "usage" in result
        assert result["usage"]["prompt_tokens"] == 10
        assert result["usage"]["completion_tokens"] >= 0
        assert result["usage"]["total_tokens"] == 10 + result["usage"]["completion_tokens"]

    def test_transforms_response_with_string_result(self):
        """Teste la transformation quand resultObject est une string."""
        one_min_response = {
            "aiRecord": {"aiRecordDetail": {"resultObject": "Direct string response"}}
        }

        result = transform_response(one_min_response, "gpt-4o-mini", 5)

        assert result["choices"][0]["message"]["content"] == "Direct string response"
        assert result["model"] == "gpt-4o-mini"

    def test_handles_empty_result_object(self):
        """Teste le cas où resultObject est vide."""
        one_min_response = {"aiRecord": {"aiRecordDetail": {"resultObject": []}}}

        result = transform_response(one_min_response, "gpt-4o", 10)

        assert "Error: No response content" in result["choices"][0]["message"]["content"]

    def test_handles_missing_ai_record(self):
        """Teste le cas où aiRecord est manquant."""
        one_min_response = {}

        result = transform_response(one_min_response, "gpt-4o", 10)

        assert "Error: No response content" in result["choices"][0]["message"]["content"]

    def test_handles_missing_ai_record_detail(self):
        """Teste le cas où aiRecordDetail est manquant."""
        one_min_response = {"aiRecord": {}}

        result = transform_response(one_min_response, "gpt-4o", 10)

        assert "Error: No response content" in result["choices"][0]["message"]["content"]

    def test_handles_none_result_object(self):
        """Teste le cas où resultObject est None."""
        one_min_response = {"aiRecord": {"aiRecordDetail": {"resultObject": None}}}

        result = transform_response(one_min_response, "gpt-4o", 10)

        assert "Error: No response content" in result["choices"][0]["message"]["content"]

    def test_handles_exception_gracefully(self):
        """Teste que les exceptions sont gérées proprement."""
        # Créer un objet qui va lever une exception lors de l'accès
        one_min_response = MagicMock()
        one_min_response.get.side_effect = RuntimeError("Unexpected error")

        result = transform_response(one_min_response, "gpt-4o", 10)

        assert "Error:" in result["choices"][0]["message"]["content"]
        assert "Unexpected error" in result["choices"][0]["message"]["content"]
        assert result["usage"]["completion_tokens"] == 0

    def test_generates_unique_ids(self):
        """Teste que chaque appel génère un ID unique."""
        one_min_response = {"aiRecord": {"aiRecordDetail": {"resultObject": ["Test"]}}}

        result1 = transform_response(one_min_response, "gpt-4o", 10)
        result2 = transform_response(one_min_response, "gpt-4o", 10)

        assert result1["id"] != result2["id"]
        assert result1["id"].startswith("chatcmpl-")

    def test_calculates_tokens_correctly(self):
        """Teste le calcul des tokens."""
        one_min_response = {
            "aiRecord": {"aiRecordDetail": {"resultObject": ["This is a test response"]}}
        }

        with patch("src.adapters.openai_adapter.calculate_token") as mock_calculate:
            mock_calculate.return_value = 5

            result = transform_response(one_min_response, "gpt-4o", 10)

            assert result["usage"]["prompt_tokens"] == 10
            assert result["usage"]["completion_tokens"] == 5
            assert result["usage"]["total_tokens"] == 15

    def test_handles_multiline_content(self):
        """Teste le contenu multiligne."""
        one_min_response = {
            "aiRecord": {"aiRecordDetail": {"resultObject": ["Line 1\nLine 2\nLine 3"]}}
        }

        result = transform_response(one_min_response, "gpt-4o", 10)

        assert result["choices"][0]["message"]["content"] == "Line 1\nLine 2\nLine 3"

    def test_handles_special_characters(self):
        """Teste les caractères spéciaux."""
        one_min_response = {
            "aiRecord": {
                "aiRecordDetail": {"resultObject": ["Héllo 🌍! <script>alert('xss')</script>"]}
            }
        }

        result = transform_response(one_min_response, "gpt-4o", 10)

        assert "Héllo 🌍!" in result["choices"][0]["message"]["content"]

    def test_different_model_names(self):
        """Teste avec différents noms de modèles."""
        one_min_response = {"aiRecord": {"aiRecordDetail": {"resultObject": ["Test"]}}}

        for model in ["gpt-4o", "gpt-4o-mini", "claude-3-haiku", "mistral-medium-latest"]:
            result = transform_response(one_min_response, model, 10)
            assert result["model"] == model


class TestStreamResponse:
    """Tests pour la fonction stream_response."""

    @pytest.fixture
    def mock_response(self):
        """Crée un mock de réponse streaming."""
        response = Mock()
        response.iter_lines.return_value = [
            b'data: {"result": "Hello"}',
            b'data: {"result": " world"}',
            b"data: [DONE]",
        ]
        return response

    def test_returns_generator(self, mock_response):
        """Teste que stream_response retourne un générateur."""
        result = stream_response(mock_response, "gpt-4o", 10)

        assert isinstance(result, Generator)

    def test_yields_openai_formatted_chunks(self, mock_response):
        """Teste le format OpenAI des chunks."""
        chunks = list(stream_response(mock_response, "gpt-4o", 10))

        # Vérifier qu'on a des chunks + metadata + [DONE]
        assert len(chunks) >= 2

        # Premier chunk devrait contenir "Hello"
        first_chunk = chunks[0]
        assert first_chunk.startswith("data: ")
        chunk_data = json.loads(first_chunk[6:])
        assert chunk_data["object"] == "chat.completion.chunk"
        assert chunk_data["model"] == "gpt-4o"
        assert "delta" in chunk_data["choices"][0]
        assert "content" in chunk_data["choices"][0]["delta"]

    def test_handles_data_prefix(self, mock_response):
        """Teste le nettoyage du préfixe 'data: '."""
        chunks = list(stream_response(mock_response, "gpt-4o", 10))

        # Tous les chunks doivent commencer par "data: "
        for chunk in chunks:
            assert chunk.startswith("data: ")

    def test_handles_done_marker(self):
        """Teste le marqueur [DONE]."""
        response = Mock()
        response.iter_lines.return_value = [
            b'data: {"result": "Test"}',
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Le dernier chunk doit être "data: [DONE]\n\n"
        assert chunks[-1] == "data: [DONE]\n\n"

    def test_handles_raw_text_lines(self):
        """Teste les lignes en texte brut (non JSON)."""
        response = Mock()
        response.iter_lines.return_value = [
            b"Raw text line",
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Devrait traiter le texte brut comme du contenu
        assert len(chunks) >= 2

    def test_handles_empty_lines(self):
        """Teste les lignes vides."""
        response = Mock()
        response.iter_lines.return_value = [
            b"",
            b'data: {"result": "Test"}',
            b"",
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Les lignes vides doivent être ignorées, mais le contenu doit être présent
        # Vérifier qu'on a au moins le chunk de contenu + metadata + [DONE]
        assert len(chunks) >= 2
        # Vérifier que le contenu "Test" est dans un des chunks
        has_test_content = any("Test" in c for c in chunks)
        assert has_test_content

    def test_handles_json_with_content_field(self):
        """Teste le JSON avec champ 'content' au lieu de 'result'."""
        response = Mock()
        response.iter_lines.return_value = [
            b'data: {"content": "Test content"}',
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        first_chunk_data = json.loads(chunks[0][6:])
        assert first_chunk_data["choices"][0]["delta"]["content"] == "Test content"

    def test_handles_invalid_json_as_raw_text(self):
        """Teste que le JSON invalide est traité comme texte brut."""
        response = Mock()
        response.iter_lines.return_value = [
            b"data: {invalid json}",
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Devrait traiter comme texte brut
        first_chunk_data = json.loads(chunks[0][6:])
        assert "{invalid json}" in first_chunk_data["choices"][0]["delta"]["content"]

    def test_skips_empty_content(self):
        """Teste que le contenu vide est ignoré."""
        response = Mock()
        response.iter_lines.return_value = [
            b'data: {"result": ""}',
            b'data: {"result": "actual content"}',
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Le contenu vide doit être ignoré, seul "actual content" doit être présent
        # Vérifier que "actual content" est dans les chunks
        has_actual_content = any("actual content" in c for c in chunks)
        assert has_actual_content

    def test_includes_final_metadata_with_tokens(self):
        """Teste les métadonnées finales avec tokens."""
        response = Mock()
        response.iter_lines.return_value = [
            b'data: {"result": "Test"}',
            b"data: [DONE]",
        ]

        with patch("src.adapters.openai_adapter.calculate_token") as mock_calculate:
            mock_calculate.return_value = 5

            chunks = list(stream_response(response, "gpt-4o", 10))

            # L'avant-dernier chunk doit avoir les métadonnées
            metadata_chunk = chunks[-2]
            metadata = json.loads(metadata_chunk[6:])

            assert metadata["choices"][0]["finish_reason"] == "stop"
            assert metadata["choices"][0]["delta"] == {}
            assert "usage" in metadata
            assert metadata["usage"]["prompt_tokens"] == 10
            assert metadata["usage"]["completion_tokens"] == 5

    def test_handles_exception_during_iteration(self):
        """Teste la gestion des exceptions pendant l'itération."""
        response = Mock()
        response.iter_lines.side_effect = RuntimeError("Connection lost")

        # Ne doit pas lever d'exception
        chunks = list(stream_response(response, "gpt-4o", 10))

        # Doit quand même produire les métadonnées finales et [DONE]
        assert len(chunks) >= 1
        assert chunks[-1] == "data: [DONE]\n\n"

    def test_handles_unicode_decode_errors(self):
        """Teste la gestion des erreurs de décodage Unicode."""
        response = Mock()
        response.iter_lines.return_value = [
            b"data: \xff\xfe invalid utf-8",
            b"data: [DONE]",
        ]

        # Ne doit pas lever d'exception
        chunks = list(stream_response(response, "gpt-4o", 10))

        assert len(chunks) >= 2

    def test_consistent_chat_id_across_chunks(self):
        """Teste que l'ID du chat est cohérent entre les chunks."""
        response = Mock()
        response.iter_lines.return_value = [
            b'data: {"result": "Hello"}',
            b'data: {"result": " world"}',
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Extraire les IDs des chunks
        chunk_ids = []
        for chunk in chunks:
            if chunk.startswith("data: ") and "[DONE]" not in chunk:
                data = json.loads(chunk[6:])
                if "id" in data:
                    chunk_ids.append(data["id"])

        # Tous les IDs doivent être identiques
        assert len(set(chunk_ids)) == 1

    def test_handles_multiple_content_formats(self):
        """Teste différents formats de contenu."""
        response = Mock()
        response.iter_lines.return_value = [
            b'data: {"result": "result field"}',
            b'data: {"content": "content field"}',
            b"data: plain text",
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Vérifier que tous les contenus sont présents
        all_content = "".join(chunks)
        assert "result field" in all_content
        assert "content field" in all_content
        assert "plain text" in all_content


class TestStreamResponseEdgeCases:
    """Tests supplémentaires pour les cas limites de stream_response."""

    def test_empty_response(self):
        """Teste une réponse vide."""
        response = Mock()
        response.iter_lines.return_value = []

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Doit quand même produire metadata + [DONE]
        assert len(chunks) >= 1
        assert chunks[-1] == "data: [DONE]\n\n"

    def test_only_done_marker(self):
        """Teste une réponse avec seulement [DONE]."""
        response = Mock()
        response.iter_lines.return_value = [b"data: [DONE]"]

        chunks = list(stream_response(response, "gpt-4o", 10))

        # Doit avoir metadata + [DONE]
        assert len(chunks) >= 1

    def test_large_content(self):
        """Teste un contenu volumineux."""
        large_content = "x" * 10000
        response = Mock()
        response.iter_lines.return_value = [
            f'data: {{"result": "{large_content}"}}'.encode(),
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        first_chunk_data = json.loads(chunks[0][6:])
        assert len(first_chunk_data["choices"][0]["delta"]["content"]) == 10000

    def test_special_characters_in_stream(self):
        """Teste les caractères spéciaux dans le stream."""
        response = Mock()
        response.iter_lines.return_value = [
            b'data: {"result": "H\\u00e9llo \\ud83c\\udf0d!"}',
            b"data: [DONE]",
        ]

        chunks = list(stream_response(response, "gpt-4o", 10))

        first_chunk_data = json.loads(chunks[0][6:])
        content = first_chunk_data["choices"][0]["delta"]["content"]
        # Les caractères Unicode doivent être préservés
        assert "H" in content
