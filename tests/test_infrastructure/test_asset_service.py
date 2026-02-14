# tests/test_infrastructure/test_asset_service.py
"""
Tests pour le service de gestion des assets (images).
"""

from unittest.mock import MagicMock, patch

import pytest
import requests


class TestDecodeBase64Image:
    """Tests pour _decode_base64_image."""

    @pytest.fixture
    def decode_fn(self):
        from src.infrastructure.asset_service import _decode_base64_image

        return _decode_base64_image

    def test_decodes_valid_png_image(self, decode_fn, sample_base64_image):
        binary_data, mime_type = decode_fn(sample_base64_image)
        assert isinstance(binary_data, bytes)
        assert len(binary_data) > 0
        assert mime_type == "image/png"

    def test_decodes_jpeg_image(self, decode_fn):
        jpeg_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
        binary_data, mime_type = decode_fn(jpeg_base64)
        assert mime_type == "image/jpeg"

    def test_raises_error_for_invalid_uri(self, decode_fn):
        invalid_data = "invalid-data-uri"
        with pytest.raises(ValueError, match="Invalid data URI"):
            decode_fn(invalid_data)

    def test_raises_error_for_missing_base64_prefix(self, decode_fn):
        invalid_data = "data:image/png,notbase64"
        with pytest.raises(ValueError):
            decode_fn(invalid_data)


class TestDownloadExternalImage:
    """Tests pour _download_external_image."""

    @pytest.fixture
    def download_fn(self):
        from src.infrastructure.asset_service import _download_external_image

        return _download_external_image

    @patch("src.infrastructure.asset_service.requests.get")
    def test_downloads_image_successfully(self, mock_get, download_fn, sample_external_image_url):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake-image-data"]
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_get.return_value = mock_response

        binary_data, mime_type = download_fn(sample_external_image_url)

        assert binary_data == b"fake-image-data"
        assert mime_type == "image/jpeg"
        mock_get.assert_called_once()

    @patch("src.infrastructure.asset_service.requests.get")
    def test_raises_error_for_large_image(self, mock_get, download_fn, sample_external_image_url):
        from src.infrastructure.asset_service import MAX_IMAGE_SIZE

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"x" * (MAX_IMAGE_SIZE + 1)]
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="FILE_TOO_LARGE_413"):
            download_fn(sample_external_image_url)

    @patch("src.infrastructure.asset_service.requests.get")
    def test_handles_http_error(self, mock_get, download_fn, sample_external_image_url):
        # B017 fix: utiliser une exception spécifique
        mock_get.side_effect = requests.RequestException("Connection failed")
        with pytest.raises(requests.RequestException):
            download_fn(sample_external_image_url)


class TestUploadImageTo1min:
    """Tests pour upload_image_to_1min."""

    @pytest.fixture
    def upload_fn(self):
        from src.infrastructure.asset_service import upload_image_to_1min

        return upload_image_to_1min

    @patch("src.infrastructure.asset_service.requests.post")
    @patch("src.infrastructure.asset_service.filetype.guess")
    def test_uploads_base64_image_successfully(
        self, mock_guess, mock_post, upload_fn, sample_base64_image, valid_api_key
    ):
        mock_kind = MagicMock()
        mock_kind.mime = "image/png"
        mock_guess.return_value = mock_kind

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"fileContent": {"path": "/uploads/test.png"}}
        mock_post.return_value = mock_response

        item = {"image_url": {"url": sample_base64_image}}
        headers = {"API-KEY": valid_api_key, "Authorization": f"Bearer {valid_api_key}"}

        result = upload_fn(item, headers, "https://api.example.com/assets")

        assert result == "/uploads/test.png"
        mock_post.assert_called_once()

    def test_raises_error_for_invalid_item(self, upload_fn):
        invalid_item = {}
        with pytest.raises(ValueError, match="Invalid 'item' structure"):
            upload_fn(invalid_item, {}, "https://api.example.com")

    def test_raises_error_for_missing_auth_header(self, upload_fn, sample_base64_image):
        item = {"image_url": {"url": sample_base64_image}}
        headers = {}
        with pytest.raises(ValueError, match="Missing API-KEY header"):
            upload_fn(item, headers, "https://api.example.com")

    @patch("src.infrastructure.asset_service.requests.post")
    @patch("src.infrastructure.asset_service.filetype.guess")
    def test_raises_error_on_api_error(
        self, mock_guess, mock_post, upload_fn, sample_base64_image, valid_api_key
    ):
        """Test que le service lève une erreur quand l'API renvoie une réponse invalide."""
        mock_kind = MagicMock()
        mock_kind.mime = "image/png"
        mock_guess.return_value = mock_kind

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        item = {"image_url": {"url": sample_base64_image}}
        headers = {"API-KEY": valid_api_key, "Authorization": f"Bearer {valid_api_key}"}

        with pytest.raises(ValueError, match="Invalid API response"):
            upload_fn(item, headers, "https://api.example.com/assets")

    @patch("src.infrastructure.asset_service.requests.post")
    @patch("src.infrastructure.asset_service.filetype.guess")
    def test_raises_error_for_missing_file_content(
        self, mock_guess, mock_post, upload_fn, sample_base64_image, valid_api_key
    ):
        """Test quand la réponse ne contient pas fileContent."""
        mock_kind = MagicMock()
        mock_kind.mime = "image/png"
        mock_guess.return_value = mock_kind

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "something went wrong"}
        mock_post.return_value = mock_response

        item = {"image_url": {"url": sample_base64_image}}
        headers = {"API-KEY": valid_api_key, "Authorization": f"Bearer {valid_api_key}"}

        with pytest.raises(ValueError, match="Invalid API response"):
            upload_fn(item, headers, "https://api.example.com/assets")
