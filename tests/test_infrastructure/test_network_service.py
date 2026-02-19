# tests/test_infrastructure/test_network_service.py
"""
Tests unitaires pour le service réseau.
Couvre handle_options_request, set_response_headers, create_json_response.
"""

import uuid
from unittest.mock import Mock, patch

from fastapi import Response
from fastapi.responses import JSONResponse

from src.infrastructure.network_service import (
    create_json_response,
    handle_options_request,
    set_response_headers,
)


class TestHandleOptionsRequest:
    """Tests pour la fonction handle_options_request."""

    def test_returns_response_object(self):
        """Teste que la fonction retourne un objet Response."""
        result = handle_options_request()

        assert isinstance(result, Response)

    def test_returns_204_status_code(self):
        """Teste que le status code est 204 (No Content)."""
        result = handle_options_request()

        assert result.status_code == 204

    def test_sets_cors_origin_header(self):
        """Teste le header Access-Control-Allow-Origin."""
        with patch("src.infrastructure.network_service.CORS_ORIGINS", "*"):
            result = handle_options_request()

            assert "Access-Control-Allow-Origin" in result.headers
            assert result.headers["Access-Control-Allow-Origin"] == "*"

    def test_sets_allow_headers(self):
        """Teste le header Access-Control-Allow-Headers."""
        result = handle_options_request()

        assert "Access-Control-Allow-Headers" in result.headers
        headers = result.headers["Access-Control-Allow-Headers"]
        assert "Content-Type" in headers
        assert "API-KEY" in headers
        assert "Authorization" in headers

    def test_sets_allow_methods(self):
        """Teste le header Access-Control-Allow-Methods."""
        result = handle_options_request()

        assert "Access-Control-Allow-Methods" in result.headers
        methods = result.headers["Access-Control-Allow-Methods"]
        assert "POST" in methods
        assert "GET" in methods
        assert "OPTIONS" in methods

    def test_sets_request_id_header(self):
        """Teste que le header X-Request-ID est présent et commence par 'opt-'."""
        result = handle_options_request()

        assert "X-Request-ID" in result.headers
        assert result.headers["X-Request-ID"].startswith("opt-")

    def test_generates_unique_request_ids(self):
        """Teste que chaque appel génère un ID unique."""
        result1 = handle_options_request()
        result2 = handle_options_request()

        assert result1.headers["X-Request-ID"] != result2.headers["X-Request-ID"]


class TestSetResponseHeaders:
    """Tests pour la fonction set_response_headers."""

    def test_returns_response_object(self):
        """Teste que la fonction retourne un objet Response."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}

        result = set_response_headers(mock_response)

        assert result is mock_response

    def test_sets_content_type(self):
        """Teste le header Content-Type."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}

        set_response_headers(mock_response)

        assert mock_response.headers["Content-Type"] == "application/json"

    def test_sets_cors_origin(self):
        """Teste le header Access-Control-Allow-Origin."""
        with patch("src.infrastructure.network_service.CORS_ORIGINS", "https://example.com"):
            mock_response = Mock(spec=Response)
            mock_response.headers = {}

            set_response_headers(mock_response)

            assert mock_response.headers["Access-Control-Allow-Origin"] == "https://example.com"

    def test_sets_request_id(self):
        """Teste le header X-Request-ID."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}

        set_response_headers(mock_response)

        assert "X-Request-ID" in mock_response.headers
        # Vérifier que c'est un UUID valide
        request_id = mock_response.headers["X-Request-ID"]
        try:
            uuid.UUID(request_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False
        assert is_valid_uuid

    def test_sets_expose_headers(self):
        """Teste le header Access-Control-Expose-Headers."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}

        set_response_headers(mock_response)

        assert mock_response.headers["Access-Control-Expose-Headers"] == "X-Request-ID"

    def test_generates_unique_request_ids(self):
        """Teste que chaque appel génère un ID unique."""
        mock_response1 = Mock(spec=Response)
        mock_response1.headers = {}
        mock_response2 = Mock(spec=Response)
        mock_response2.headers = {}

        set_response_headers(mock_response1)
        set_response_headers(mock_response2)

        assert mock_response1.headers["X-Request-ID"] != mock_response2.headers["X-Request-ID"]

    def test_preserves_existing_headers(self):
        """Teste que les headers existants sont préservés."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {"X-Custom-Header": "custom-value"}

        set_response_headers(mock_response)

        assert mock_response.headers["X-Custom-Header"] == "custom-value"


class TestCreateJsonResponse:
    """Tests pour la fonction create_json_response."""

    def test_returns_json_response_object(self):
        """Teste que la fonction retourne un objet JSONResponse."""
        result = create_json_response({"key": "value"})

        assert isinstance(result, JSONResponse)

    def test_default_status_code_is_200(self):
        """Teste que le status code par défaut est 200."""
        result = create_json_response({"key": "value"})

        assert result.status_code == 200

    def test_custom_status_code(self):
        """Teste qu'un status code personnalisé est appliqué."""
        result = create_json_response({"error": "not found"}, status_code=404)

        assert result.status_code == 404

    def test_sets_content_type_header(self):
        """Teste le header Content-Type."""
        result = create_json_response({"key": "value"})

        assert result.headers["Content-Type"] == "application/json"

    def test_sets_cors_origin_header(self):
        """Teste le header Access-Control-Allow-Origin."""
        with patch("src.infrastructure.network_service.CORS_ORIGINS", "*"):
            result = create_json_response({"key": "value"})

            assert result.headers["Access-Control-Allow-Origin"] == "*"

    def test_sets_request_id_header(self):
        """Teste le header X-Request-ID."""
        result = create_json_response({"key": "value"})

        assert "X-Request-ID" in result.headers
        # Vérifier que c'est un UUID valide
        request_id = result.headers["X-Request-ID"]
        try:
            uuid.UUID(request_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False
        assert is_valid_uuid

    def test_sets_expose_headers(self):
        """Teste le header Access-Control-Expose-Headers."""
        result = create_json_response({"key": "value"})

        assert result.headers["Access-Control-Expose-Headers"] == "X-Request-ID"

    def test_generates_unique_request_ids(self):
        """Teste que chaque appel génère un ID unique."""
        result1 = create_json_response({"key": "value1"})
        result2 = create_json_response({"key": "value2"})

        assert result1.headers["X-Request-ID"] != result2.headers["X-Request-ID"]

    def test_with_empty_content(self):
        """Teste avec un contenu vide."""
        result = create_json_response({})

        assert result.status_code == 200
        assert isinstance(result, JSONResponse)

    def test_with_complex_content(self):
        """Teste avec un contenu complexe."""
        content = {
            "nested": {
                "key": "value",
                "list": [1, 2, 3],
            },
            "items": [{"id": 1}, {"id": 2}],
        }
        result = create_json_response(content)

        assert result.status_code == 200
        assert isinstance(result, JSONResponse)

    def test_various_status_codes(self):
        """Teste différents status codes."""
        test_cases = [
            (200, "OK"),
            (201, "Created"),
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
        ]

        for status_code, _ in test_cases:
            result = create_json_response({"status": "test"}, status_code=status_code)
            assert result.status_code == status_code


class TestNetworkServiceIntegration:
    """Tests d'intégration pour le service réseau."""

    def test_all_functions_use_same_cors_config(self):
        """Teste que toutes les fonctions utilisent la même config CORS."""
        with patch("src.infrastructure.network_service.CORS_ORIGINS", "https://test.com"):
            options_response = handle_options_request()
            mock_response = Mock(spec=Response)
            mock_response.headers = {}
            set_response_headers(mock_response)
            json_response = create_json_response({"test": "value"})

            assert options_response.headers["Access-Control-Allow-Origin"] == "https://test.com"
            assert mock_response.headers["Access-Control-Allow-Origin"] == "https://test.com"
            assert json_response.headers["Access-Control-Allow-Origin"] == "https://test.com"

    def test_all_functions_generate_request_ids(self):
        """Teste que toutes les fonctions génèrent des IDs de requête."""
        options_response = handle_options_request()
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        set_response_headers(mock_response)
        json_response = create_json_response({"test": "value"})

        # Tous doivent avoir un X-Request-ID
        assert "X-Request-ID" in options_response.headers
        assert "X-Request-ID" in mock_response.headers
        assert "X-Request-ID" in json_response.headers

        # Tous les IDs doivent être différents
        ids = [
            options_response.headers["X-Request-ID"],
            mock_response.headers["X-Request-ID"],
            json_response.headers["X-Request-ID"],
        ]
        assert len(set(ids)) == 3
