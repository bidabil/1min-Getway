# ============================================================================
# src/infrastructure/adapters/one_min_asset_adapter.py - IMPLÉMENTATION
# ============================================================================
import logging

from ...domain.ports import AssetServicePort

logger = logging.getLogger("1min-gateway.asset-adapter")


class OneMinAssetAdapter(AssetServicePort):
    """Implémentation concrète du service d'assets pour 1min.ai"""

    def __init__(self, asset_url: str):
        self._asset_url = asset_url

    def upload_image(self, image_data: dict, api_key: str) -> str:
        """Implémentation de l'upload d'image"""
        # Import local pour éviter les dépendances circulaires
        from ..asset_service import upload_image_to_1min

        headers = {"API-KEY": api_key}
        return upload_image_to_1min(image_data, headers, self._asset_url)
