# tests/test_error_service.py
"""
Tests pour le service de gestion des erreurs.
"""
import json

import pytest


def test_error_service_codes():
    """Test tous les codes d'erreur définis."""
    from src.infrastructure.error_service import get_error_response

    test_cases = [
        (1002, 404, "model_not_found"),
        (1020, 401, "invalid_api_key"),
        (1021, 401, "invalid_api_key"),
        (1212, 400, "model_not_supported"),
        (1044, 400, "model_not_supported"),
        (1412, 400, "invalid_request_error"),
        (1423, 400, "invalid_request_error"),
        (1405, 405, "method_not_allowed"),
        (413, 413, "file_too_large"),
        (500, 500, "internal_error"),
    ]

    for code, expected_status, expected_code in test_cases:
        error_payload, status = get_error_response(code, model="test-model")

        assert status == expected_status
        assert error_payload["type"] is not None
        if expected_code:
            assert error_payload["code"] == expected_code


def test_error_service_unknown_code():
    """Test avec un code d'erreur inconnu."""
    from src.infrastructure.error_service import get_error_response

    error_payload, status = get_error_response(9999, model="test-model")

    assert status == 400
    assert error_payload["type"] == "unknown_error"


def test_error_service_with_model_name():
    """Test que le nom du modèle est correctement inséré dans le message."""
    from src.infrastructure.error_service import get_error_response

    error_payload, status = get_error_response(1002, model="gpt-5-ultra")

    assert status == 404
    assert "gpt-5-ultra" in error_payload["message"]
    assert error_payload["code"] == "model_not_found"


def test_error_service_without_model():
    """Test sans nom de modèle."""
    from src.infrastructure.error_service import get_error_response

    error_payload, status = get_error_response(1020)

    assert status == 401
    assert "Incorrect API key provided" in error_payload["message"]
    assert error_payload["code"] == "invalid_api_key"
