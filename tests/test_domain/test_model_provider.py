# tests/test_domain/test_model_provider.py
"""
Tests pour le fournisseur de modèles.
Utilise fixtures et tests paramétrés.
"""

import pytest


class TestGetFormattedModelsList:
    """Tests pour get_formatted_models_list."""

    @pytest.fixture
    def get_models_fn(self):
        """Importe la fonction à tester."""
        from src.domain.model_provider import get_formatted_models_list

        return get_formatted_models_list

    # --- Tests catalogue complet ---
    def test_full_catalog_returns_all_models(self, get_models_fn, available_models):
        # Arrange & Act
        result = get_models_fn(
            all_models=available_models,
            permit_subset_only=False,
            subset_models=[],
        )

        # Assert
        assert len(result) == len(available_models)

    def test_model_format_is_openai_compatible(self, get_models_fn, available_models):
        # Arrange & Act
        result = get_models_fn(
            all_models=available_models,
            permit_subset_only=False,
            subset_models=[],
        )

        # Assert
        for model in result:
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"
            assert "owned_by" in model
            assert model["owned_by"] == "1min-gateway"
            assert "created" in model

    # --- Tests sous-ensemble ---
    def test_subset_restriction_filters_models(self, get_models_fn):
        # Arrange
        all_models = ["gpt-4o", "claude-3-haiku", "mistral-medium"]
        subset = ["gpt-4o", "mistral-medium"]

        # Act
        result = get_models_fn(
            all_models=all_models,
            permit_subset_only=True,
            subset_models=subset,
        )

        # Assert
        assert len(result) == 2
        model_ids = [m["id"] for m in result]
        assert "gpt-4o" in model_ids
        assert "mistral-medium" in model_ids
        assert "claude-3-haiku" not in model_ids

    # --- Tests edge cases ---
    def test_empty_all_models_returns_empty_list(self, get_models_fn):
        # Arrange & Act
        result = get_models_fn(
            all_models=[],
            permit_subset_only=False,
            subset_models=[],
        )

        # Assert
        assert result == []

    def test_empty_subset_when_restricted_returns_empty(self, get_models_fn, available_models):
        # Arrange & Act
        result = get_models_fn(
            all_models=available_models,
            permit_subset_only=True,
            subset_models=[],  # Sous-ensemble vide
        )

        # Assert
        assert result == []

    def test_special_characters_in_model_names(self, get_models_fn):
        # Arrange
        all_models = ["gpt-4o", "model/v1.0", "model@latest"]

        # Act
        result = get_models_fn(
            all_models=all_models,
            permit_subset_only=False,
            subset_models=[],
        )

        # Assert
        assert len(result) == 3
        model_ids = [m["id"] for m in result]
        assert "model/v1.0" in model_ids
        assert "model@latest" in model_ids

    @pytest.mark.parametrize(
        "all_models,subset,permit_only,expected_count",
        [
            (["a", "b", "c"], [], False, 3),
            (["a", "b", "c"], ["a"], True, 1),
            (["a", "b", "c"], ["a", "b"], True, 2),
            ([], [], False, 0),
            (["a"], [], True, 0),
        ],
    )
    def test_various_combinations(
        self, get_models_fn, all_models, subset, permit_only, expected_count
    ):
        result = get_models_fn(
            all_models=all_models,
            permit_subset_only=permit_only,
            subset_models=subset,
        )
        assert len(result) == expected_count
