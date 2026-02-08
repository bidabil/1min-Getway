# tests/test_infrastructure/test_asset_service.py
"""
Tests pour le service de gestion des assets (images).
"""
import base64
import json
from unittest.mock import MagicMock, patch

import pytest

# Test data
SAMPLE_IMAGE_BASE64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
SAMPLE_IMAGE_URL = "https://example.com/image.jpg"


class TestAssetService:
    """Tests pour le service d'assets."""

    def test_decode_base64_image_success(self):
        """Test le décodage d'une image base64."""
        from src.infrastructure.asset_service import _decode_base64_image

        binary_data, mime_type = _decode_base64_image(SAMPLE_IMAGE_BASE64)

        assert isinstance(binary_data, bytes)
        assert len(binary_data) > 0
        assert mime_type == "image/png"

    def test_decode_base64_image_invalid(self):
        """Test avec une URI base64 invalide."""
        from src.infrastructure.asset_service import _decode_base64_image

        with pytest.raises(ValueError, match="Invalid data URI"):
            _decode_base64_image("invalid-data")

    @patch("src.infrastructure.asset_service.requests.get")
    def test_download_external_image_success(self, mock_get):
        """Test le téléchargement d'une image externe."""
        from src.infrastructure.asset_service import _download_external_image

        # Mock la réponse HTTP
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake-image-data"]
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_get.return_value = mock_response

        binary_data, mime_type = _download_external_image(SAMPLE_IMAGE_URL)

        assert isinstance(binary_data, bytes)
        assert binary_data == b"fake-image-data"
        assert mime_type == "image/jpeg"
        mock_get.assert_called_once()

    @patch("src.infrastructure.asset_service.requests.get")
    def test_download_external_image_too_large(self, mock_get):
        """Test le rejet d'une image trop volumineuse."""
        from src.infrastructure.asset_service import MAX_IMAGE_SIZE, _download_external_image

        # Mock une image trop grande
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simuler beaucoup de données
        mock_response.iter_content.return_value = [b"x" * (MAX_IMAGE_SIZE + 1)]
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="FILE_TOO_LARGE_413"):
            _download_external_image(SAMPLE_IMAGE_URL)

    @patch("src.infrastructure.asset_service.requests.post")
    @patch("src.infrastructure.asset_service.filetype.guess")
    def test_upload_image_to_1min_base64(self, mock_guess, mock_post):
        """Test l'upload d'une image base64 vers 1min.ai."""
        from src.infrastructure.asset_service import upload_image_to_1min

        # Mock filetype
        mock_kind = MagicMock()
        mock_kind.mime = "image/png"
        mock_guess.return_value = mock_kind

        # Mock la réponse de l'API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"fileContent": {"path": "/uploads/test-image.png"}}
        mock_post.return_value = mock_response

        # Données de test
        item = {"image_url": {"url": SAMPLE_IMAGE_BASE64}}
        headers = {"API-KEY": "test-key", "Authorization": "Bearer test-key"}

        result = upload_image_to_1min(item, headers, "https://api.example.com/assets")

        assert result == "/uploads/test-image.png"
        mock_post.assert_called_once()

    def test_upload_image_to_1min_invalid_item(self):
        """Test avec un item invalide."""
        from src.infrastructure.asset_service import upload_image_to_1min

        with pytest.raises(ValueError, match="Invalid 'item' structure"):
            upload_image_to_1min({}, {}, "https://api.example.com/assets")

    def test_upload_image_to_1min_invalid_headers(self):
        """Test avec des headers invalides."""
        from src.infrastructure.asset_service import upload_image_to_1min

        item = {"image_url": {"url": SAMPLE_IMAGE_BASE64}}

        with pytest.raises(ValueError, match="Missing or invalid Authorization header"):
            upload_image_to_1min(item, {}, "https://api.example.com/assets")
