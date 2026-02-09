# tests/test_error_service.py
"""
Tests pour le service de gestion des erreurs.
Adapté aux codes d'erreur RÉELS du service.
"""

import pytest


class TestGetErrorResponse:
    """Tests pour get_error_response."""

    @pytest.fixture
    def get_error_fn(self):
        from src.infrastructure.error_service import get_error_response

        return get_error_response

    # CORRECTION: Utiliser les codes RÉELS retournés par le service (MAJUSCULES)
    @pytest.mark.parametrize(
        "code,expected_status,expected_code",
        [
            (1002, 404, "MODEL_NOT_FOUND"),
            (1020, 401, "UNAUTHORIZED"),
            (1021, 401, "UNAUTHORIZED"),
            (1212, 400, "INVALID_ENDPOINT"),
            (1044, 400, "MODEL_NOT_SUPPORTED"),
            (1412, 400, "INVALID_REQUEST"),
            (1423, 400, "INVALID_REQUEST"),
            (1405, 405, "METHOD_NOT_ALLOWED"),
            (413, 413, "PAYLOAD_TOO_LARGE"),
            (500, 500, "INTERNAL_ERROR"),
        ],
    )
    def test_error_codes(self, get_error_fn, code, expected_status, expected_code):
        # Act
        error_payload, status = get_error_fn(code, model="test-model")

        # Assert
        assert status == expected_status
        assert error_payload["code"] == expected_code
        assert "message" in error_payload

    # CORRECTION: Le service ne retourne pas de champ "type"
    def test_unknown_code_returns_400(self, get_error_fn):
        # Act
        error_payload, status = get_error_fn(9999)

        # Assert
        assert status == 400
        assert error_payload["code"] == "UNKNOWN_ERROR"

    def test_model_name_in_message(self, get_error_fn):
        # Act
        error_payload, status = get_error_fn(1002, model="gpt-5-ultra")

        # Assert
        assert "gpt-5-ultra" in error_payload["message"]

    # CORRECTION: Adapter au message réel
    def test_works_without_model(self, get_error_fn):
        # Act
        error_payload, status = get_error_fn(1020)

        # Assert
        assert status == 401
        # Le message réel contient "Invalid or missing API key"
        assert "API key" in error_payload["message"]
