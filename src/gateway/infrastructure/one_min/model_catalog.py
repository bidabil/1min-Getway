"""Adapter for 1min.ai's public model catalog: GET /models?feature=TYPE.

This is the catalog the 1min.ai documentation uses to list the models of each feature.
"""

import time
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlencode

from ...domain.errors import UpstreamError
from ...domain.models import Backend, ModelInfo
from .http import OneMinHttp

CATALOG_PATH = "/models"


class PublicModelCatalog:
    def __init__(self, http: OneMinHttp, *, timeout_s: float = 15.0, ttl_s: float = 600.0) -> None:
        self._http = http
        self._timeout = timeout_s
        self._ttl = ttl_s
        self._cache: dict[str, tuple[float, tuple[ModelInfo, ...]]] = {}

    async def models_for(self, feature_type: str) -> Sequence[ModelInfo]:
        feature = feature_type.upper()
        cached = self._cache.get(feature)
        if cached is not None and time.monotonic() < cached[0]:
            return cached[1]
        data = await self._http.get_json(
            f"{CATALOG_PATH}?{urlencode({'feature': feature})}",
            auth="api_key",
            timeout_s=self._timeout,
        )
        models = tuple(parse_catalog(data, feature))
        self._cache[feature] = (time.monotonic() + self._ttl, models)
        return models


def parse_catalog(data: Any, feature: str) -> list[ModelInfo]:
    items = data.get("models") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise UpstreamError("1min.ai returned an unexpected model catalog.")
    models: list[ModelInfo] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("modelId"), str):
            continue
        if str(item.get("status") or "ACTIVE").upper() != "ACTIVE":
            continue
        features = item.get("features")
        if isinstance(features, list) and feature not in features:
            continue
        models.append(
            ModelInfo(
                id=item["modelId"],
                backend=Backend.LEGACY,
                owned_by=str(item.get("provider") or "1min-ai"),
                name=item.get("name") if isinstance(item.get("name"), str) else None,
                vision=_accepts_images(item.get("modality")),
                max_output_tokens=_max_output(item.get("creditMetadata")),
                deprecation_date=item.get("deprecationDate")
                if isinstance(item.get("deprecationDate"), str)
                else None,
            )
        )
    return models


def _accepts_images(modality: Any) -> bool | None:
    if not isinstance(modality, dict) or not isinstance(modality.get("INPUT"), list):
        return None
    return any(str(kind).lower() == "image" for kind in modality["INPUT"])


def _max_output(metadata: Any) -> int | None:
    value = metadata.get("MAX_OUTPUT_TOKEN") if isinstance(metadata, dict) else None
    return int(value) if isinstance(value, int | float) and value > 0 else None
