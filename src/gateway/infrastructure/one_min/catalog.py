"""Static catalog of 1min.ai feature types, loaded from package data."""

import json
from collections.abc import Sequence
from importlib import resources
from typing import Any, Literal

from ...domain.features import FeatureField, FeatureSpec


class StaticFeatureCatalog:
    def __init__(self, specs: Sequence[FeatureSpec]) -> None:
        self._specs = tuple(specs)
        self._by_type = {spec.type: spec for spec in self._specs}

    @classmethod
    def load_default(cls) -> "StaticFeatureCatalog":
        raw = (
            resources.files(__package__).joinpath("data/features.json").read_text(encoding="utf-8")
        )
        return cls.from_json(json.loads(raw))

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StaticFeatureCatalog":
        return cls([_spec(item) for item in data.get("features", [])])

    def list(self) -> Sequence[FeatureSpec]:
        return self._specs

    def get(self, feature_type: str) -> FeatureSpec | None:
        return self._by_type.get(feature_type.upper())


def _spec(item: dict[str, Any]) -> FeatureSpec:
    conversation_id: Literal["type", "none"] = (
        "type" if item.get("conversation_id") == "type" else "none"
    )
    return FeatureSpec(
        type=str(item["type"]).upper(),
        category=str(item.get("category", "other")),
        title=str(item.get("title", item["type"])),
        description=str(item.get("description", "")),
        models=tuple(str(model) for model in item.get("models", [])),
        fields=tuple(
            FeatureField(
                name=str(field["name"]),
                type=str(field.get("type", "string")),
                required=bool(field.get("required", False)),
                description=field.get("description"),
                enum=tuple(str(value) for value in field.get("enum", [])),
                default=field.get("default"),
            )
            for field in item.get("fields", [])
        ),
        conversation_id=conversation_id,
        long_running=bool(item.get("long_running", False)),
        docs_url=item.get("docs_url"),
    )
