# tests/test_infrastructure/test_api_key_validator.py
"""
Tests unitaires pour le service de validation des clés API.
"""

from unittest.mock import MagicMock, patch

import requests

from src.infrastructure.api_key_validator import ApiKeyValidator, api_key_validator


class TestApiKeyValidatorFormatOnly:
    """Tests pour la validation de format uniquement."""

    def test_returns_false_for_empty_key(self):
        """Une clé vide doit être rejetée."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate_format_only("")
        assert is_valid is False
        assert error == "Missing API key"

    def test_returns_false_for_none_key(self):
        """Une clé None doit être rejetée."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate_format_only(None)
        assert is_valid is False
        assert error == "Missing API key"

    def test_returns_false_for_short_key(self):
        """Une clé trop courte doit être rejetée."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate_format_only("short-key-1234567890")
        assert is_valid is False
        assert "too short" in error.lower()

    def test_returns_false_for_very_short_key(self):
        """Une clé très courte doit être rejetée."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate_format_only("abc")
        assert is_valid is False
        assert "too short" in error.lower()

    def test_returns_false_for_long_key(self):
        """Une clé trop longue doit être rejetée."""
        validator = ApiKeyValidator()
        long_key = "a" * 150
        is_valid, error = validator.validate_format_only(long_key)
        assert is_valid is False
        assert "too long" in error.lower()

    def test_returns_false_for_invalid_characters(self):
        """Une clé avec des caractères invalides doit être rejetée."""
        validator = ApiKeyValidator()
        # Clé avec des caractères spéciaux invalides
        invalid_key = "valid-length-key-with-special-chars-!@#$%"
        is_valid, error = validator.validate_format_only(invalid_key)
        assert is_valid is False
        assert "invalid characters" in error.lower()

    def test_returns_true_for_valid_alphanumeric_key(self):
        """Une clé alphanumérique valide doit être acceptée."""
        validator = ApiKeyValidator()
        valid_key = "abcdefghijklmnopqrstuvwxyz123456"  # pragma: allowlist secret
        is_valid, error = validator.validate_format_only(valid_key)
        assert is_valid is True
        assert error is None

    def test_returns_true_for_key_with_underscores(self):
        """Une clé avec des underscores doit être acceptée."""
        validator = ApiKeyValidator()
        valid_key = "valid_key_with_underscores_12345678901234"  # pragma: allowlist secret
        is_valid, error = validator.validate_format_only(valid_key)
        assert is_valid is True
        assert error is None

    def test_returns_true_for_key_with_dashes(self):
        """Une clé avec des tirets doit être acceptée."""
        validator = ApiKeyValidator()
        valid_key = "valid-key-with-dashes-123456789012345"
        is_valid, error = validator.validate_format_only(valid_key)
        assert is_valid is True
        assert error is None

    def test_returns_true_for_mixed_format_key(self):
        """Une clé avec format mixte doit être acceptée."""
        validator = ApiKeyValidator()
        valid_key = "MixedCase_Key-12345678901234567890"
        is_valid, error = validator.validate_format_only(valid_key)
        assert is_valid is True
        assert error is None

    def test_accepts_exactly_32_chars(self):
        """Une clé d'exactement 32 caractères doit être acceptée."""
        validator = ApiKeyValidator()
        valid_key = "a" * 32
        is_valid, error = validator.validate_format_only(valid_key)
        assert is_valid is True
        assert error is None

    def test_accepts_exactly_128_chars(self):
        """Une clé d'exactement 128 caractères doit être acceptée."""
        validator = ApiKeyValidator()
        valid_key = "a" * 128
        is_valid, error = validator.validate_format_only(valid_key)
        assert is_valid is True
        assert error is None

    def test_rejects_31_chars(self):
        """Une clé de 31 caractères doit être rejetée."""
        validator = ApiKeyValidator()
        short_key = "a" * 31
        is_valid, error = validator.validate_format_only(short_key)
        assert is_valid is False
        assert "too short" in error.lower()

    def test_rejects_129_chars(self):
        """Une clé de 129 caractères doit être rejetée."""
        validator = ApiKeyValidator()
        long_key = "a" * 129
        is_valid, error = validator.validate_format_only(long_key)
        assert is_valid is False
        assert "too long" in error.lower()


class TestApiKeyValidatorValidate:
    """Tests pour la validation complète via API."""

    def test_returns_false_for_empty_key(self):
        """Une clé vide doit être rejetée sans appel API."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate("")
        assert is_valid is False
        assert error == "Missing API key"

    def test_returns_false_for_none_key(self):
        """Une clé None doit être rejetée sans appel API."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate(None)
        assert is_valid is False
        assert error == "Missing API key"

    def test_returns_false_for_short_key(self):
        """Une clé trop courte doit être rejetée sans appel API."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate("short-key")
        assert is_valid is False
        assert "too short" in error.lower()

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_returns_true_for_valid_key(self, mock_get):
        """Une clé valide doit retourner True."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        validator = ApiKeyValidator()
        is_valid, error = validator.validate("valid-api-key-12345678901234567890")

        assert is_valid is True
        assert error is None
        mock_get.assert_called_once()

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_returns_false_for_unauthorized_key(self, mock_get):
        """Une clé non autorisée (401) doit retourner False."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        validator = ApiKeyValidator()
        is_valid, error = validator.validate("invalid-api-key-12345678901234567")

        assert is_valid is False
        assert "Authentication failed" in error

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_returns_false_for_forbidden_key(self, mock_get):
        """Une clé sans permissions (403) doit retourner False."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        validator = ApiKeyValidator()
        is_valid, error = validator.validate("forbidden-api-key-123456789012345")

        assert is_valid is False
        assert "permissions" in error.lower()

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_fail_open_on_server_error(self, mock_get):
        """En cas d'erreur serveur (500), la clé doit être acceptée (fail-open)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        validator = ApiKeyValidator()
        is_valid, error = validator.validate("test-api-key-12345678901234567890")

        assert is_valid is True
        assert error is None

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_fail_open_on_timeout(self, mock_get):
        """En cas de timeout, la clé doit être acceptée (fail-open)."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        validator = ApiKeyValidator()
        is_valid, error = validator.validate("test-api-key-12345678901234567890")

        assert is_valid is True
        assert "timeout" in error.lower()

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_fail_open_on_connection_error(self, mock_get):
        """En cas d'erreur de connexion, la clé doit être acceptée (fail-open)."""
        mock_get.side_effect = requests.exceptions.ConnectionError("No connection")

        validator = ApiKeyValidator()
        is_valid, error = validator.validate("test-api-key-12345678901234567890")

        assert is_valid is True
        assert "unreachable" in error.lower()

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_fail_open_on_unexpected_error(self, mock_get):
        """En cas d'erreur inattendue, la clé doit être acceptée (fail-open)."""
        mock_get.side_effect = Exception("Unexpected error")

        validator = ApiKeyValidator()
        is_valid, error = validator.validate("test-api-key-12345678901234567890")

        assert is_valid is True
        assert "error" in error.lower()

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_sends_api_key_in_header(self, mock_get):
        """La clé API doit être envoyée dans le header API-KEY."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        validator = ApiKeyValidator()
        validator.validate("test-api-key-12345678901234567890")

        call_args = mock_get.call_args
        assert "headers" in call_args.kwargs
        assert call_args.kwargs["headers"]["API-KEY"] == "test-api-key-12345678901234567890"

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_uses_correct_endpoint(self, mock_get):
        """L'endpoint correct doit être utilisé."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        validator = ApiKeyValidator(base_url="https://api.test.com")
        validator.validate("test-api-key-12345678901234567890")

        call_args = mock_get.call_args
        assert "https://api.test.com/api/user-info" in call_args.args[0]

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_uses_timeout(self, mock_get):
        """Un timeout doit être configuré."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        validator = ApiKeyValidator()
        validator.validate("test-api-key-12345678901234567890")

        call_args = mock_get.call_args
        assert "timeout" in call_args.kwargs
        assert call_args.kwargs["timeout"] == 10


class TestApiKeyValidatorGlobalInstance:
    """Tests pour l'instance globale."""

    def test_global_instance_exists(self):
        """L'instance globale doit exister."""
        assert api_key_validator is not None

    def test_global_instance_is_validator(self):
        """L'instance globale doit être un ApiKeyValidator."""
        assert isinstance(api_key_validator, ApiKeyValidator)

    def test_global_instance_can_validate_format(self):
        """L'instance globale doit pouvoir valider le format."""
        is_valid, _ = api_key_validator.validate_format_only(
            "valid-key-123456789012345678901234567890"
        )
        assert is_valid is True


class TestApiKeyValidatorEdgeCases:
    """Tests pour les cas limites."""

    def test_whitespace_only_key(self):
        """Une clé avec uniquement des espaces doit être rejetée."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate_format_only("                                   ")
        assert is_valid is False
        assert "invalid characters" in error.lower()

    def test_key_with_unicode(self):
        """Une clé avec des caractères unicode doit être rejetée."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate_format_only("clé-avec-accents-123456789012345678")
        assert is_valid is False
        assert "invalid characters" in error.lower()

    def test_key_with_spaces(self):
        """Une clé avec des espaces doit être rejetée."""
        validator = ApiKeyValidator()
        is_valid, error = validator.validate_format_only("key with spaces-123456789012345678")
        assert is_valid is False
        assert "invalid characters" in error.lower()

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_various_server_error_codes(self, mock_get):
        """Différents codes d'erreur serveur doivent être gérés en fail-open."""
        for status_code in [500, 502, 503, 504]:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_get.return_value = mock_response

            validator = ApiKeyValidator()
            is_valid, error = validator.validate("test-api-key-12345678901234567890")

            assert is_valid is True, f"Expected True for status {status_code}"
            assert error is None

    @patch("src.infrastructure.api_key_validator.requests.get")
    def test_various_client_error_codes(self, mock_get):
        """Différents codes d'erreur client doivent être gérés."""
        # 400 Bad Request - fail-open
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        validator = ApiKeyValidator()
        is_valid, error = validator.validate("test-api-key-12345678901234567890")
        assert is_valid is True  # fail-open

    def test_validate_returns_tuple(self):
        """validate doit toujours retourner un tuple."""
        validator = ApiKeyValidator()
        result = validator.validate("")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_validate_format_only_returns_tuple(self):
        """validate_format_only doit toujours retourner un tuple."""
        validator = ApiKeyValidator()
        result = validator.validate_format_only("")
        assert isinstance(result, tuple)
        assert len(result) == 2
