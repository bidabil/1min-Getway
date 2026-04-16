# tests/test_infrastructure/test_network_service.py
"""
Tests unitaires pour le service réseau.
Couvre handle_options_request, set_response_headers.
"""

import uuid
from unittest.mock import Mock, patch

from fastapi import Response

from src.infrastructure.network_service import (
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


class TestNetworkServiceIntegration:
    """Tests d'intégration pour le service réseau."""

    def test_options_and_response_use_same_cors_config(self):
        """Teste que les deux fonctions utilisent la même config CORS."""
        with patch("src.infrastructure.network_service.CORS_ORIGINS", "https://test.com"):
            options_response = handle_options_request()
            mock_response = Mock(spec=Response)
            mock_response.headers = {}
            set_response_headers(mock_response)

            assert options_response.headers["Access-Control-Allow-Origin"] == "https://test.com"
            assert mock_response.headers["Access-Control-Allow-Origin"] == "https://test.com"

    def test_both_functions_generate_request_ids(self):
        """Teste que les deux fonctions génèrent des IDs de requête."""
        options_response = handle_options_request()
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        set_response_headers(mock_response)

        assert "X-Request-ID" in options_response.headers
        assert "X-Request-ID" in mock_response.headers
        assert options_response.headers["X-Request-ID"] != mock_response.headers["X-Request-ID"]


class TestEmptyCorsOrigins:
    """Tests pour le cas où CORS_ORIGINS est vide (sécurité par défaut)."""

    def test_options_request_no_cors_header_when_empty(self):
        """Teste que le header CORS n'est pas ajouté quand CORS_ORIGINS est vide."""
        with patch("src.infrastructure.network_service.CORS_ORIGINS", ""):
            result = handle_options_request()

            # Le header CORS ne doit pas être présent
            assert "Access-Control-Allow-Origin" not in result.headers
            # Les autres headers doivent être présents
            assert "Access-Control-Allow-Headers" in result.headers
            assert "Access-Control-Allow-Methods" in result.headers

    def test_set_response_headers_no_cors_when_empty(self):
        """Teste que le header CORS n'est pas ajouté quand CORS_ORIGINS est vide."""
        with patch("src.infrastructure.network_service.CORS_ORIGINS", ""):
            mock_response = Mock(spec=Response)
            mock_response.headers = {}

            set_response_headers(mock_response)

            # Le header CORS ne doit pas être présent
            assert "Access-Control-Allow-Origin" not in mock_response.headers
            # Les autres headers doivent être présents
            assert mock_response.headers["Content-Type"] == "application/json"
            assert "X-Request-ID" in mock_response.headers
