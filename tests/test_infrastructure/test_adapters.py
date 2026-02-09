# tests/test_infrastructure/test_adapters.py
"""
Tests pour les adapters d'infrastructure.
CORRECTION: Les mocks doivent cibler le bon chemin d'import.
"""

from unittest.mock import patch


class TestOneMinAssetAdapter:
    """Tests pour l'adapter d'assets."""

    def test_implements_asset_service_port(self):
        # Arrange
        from src.domain.ports import AssetServicePort
        from src.infrastructure.adapters.one_min_asset_adapter import OneMinAssetAdapter

        # Act
        adapter = OneMinAssetAdapter("https://api.example.com")

        # Assert
        assert isinstance(adapter, AssetServicePort)

    # CORRECTION: Mock le bon chemin (où la fonction est IMPORTÉE, pas où elle est définie)
    @patch("src.infrastructure.asset_service.upload_image_to_1min")
    def test_upload_image_delegates_to_service(self, mock_upload):
        # Arrange
        from src.infrastructure.adapters.one_min_asset_adapter import OneMinAssetAdapter

        mock_upload.return_value = "/uploads/test.png"
        adapter = OneMinAssetAdapter("https://api.example.com")
        image_data = {"image_url": {"url": "data:image/png;base64,xxx"}}

        # Act
        result = adapter.upload_image(image_data, "test-key")

        # Assert
        assert result == "/uploads/test.png"


class TestOneMinConversationAdapter:
    """Tests pour l'adapter de conversation."""

    def test_implements_conversation_service_port(self):
        # Arrange
        from src.domain.ports import ConversationServicePort
        from src.infrastructure.adapters.one_min_conversation_adapter import (
            OneMinConversationAdapter,
        )

        # Act
        adapter = OneMinConversationAdapter()

        # Assert
        assert isinstance(adapter, ConversationServicePort)

    # CORRECTION: Mock le bon chemin
    @patch("src.infrastructure.one_min_client.create_1min_conversation")
    def test_create_conversation_delegates_to_client(self, mock_create):
        # Arrange
        from src.infrastructure.adapters.one_min_conversation_adapter import (
            OneMinConversationAdapter,
        )

        mock_create.return_value = "uuid-123"
        adapter = OneMinConversationAdapter()

        # Act
        result = adapter.create_conversation(
            api_key="key",  # pragma: allowlist secret
            model="gpt-4o",
            conv_type="CHAT_WITH_PDF",
            title="Test",
            file_ids=["file-1"],
        )

        # Assert
        assert result == "uuid-123"


class TestTiktokenAdapter:
    """Tests pour l'adapter de tokens."""

    def test_implements_token_service_port(self):
        # Arrange
        from src.domain.ports import TokenServicePort
        from src.infrastructure.adapters.token_adapter import TiktokenAdapter

        # Act
        adapter = TiktokenAdapter()

        # Assert
        assert isinstance(adapter, TokenServicePort)

    # CORRECTION: Mock le bon chemin
    @patch("src.infrastructure.token_service.calculate_token")
    def test_calculate_delegates_to_service(self, mock_calc):
        # Arrange
        from src.infrastructure.adapters.token_adapter import TiktokenAdapter

        mock_calc.return_value = 5
        adapter = TiktokenAdapter()

        # Act
        result = adapter.calculate("Hello", "gpt-4o")

        # Assert
        assert result == 5
