import os
from src.domain.models import ALL_ONE_MIN_AVAILABLE_MODELS

# --- URLs et Constantes (Valeurs Magiques) ---
ONE_MIN_API_URL = "https://api.1min.ai/api/features"
ONE_MIN_CONVERSATION_API_URL = "https://api.1min.ai/api/conversations"
ONE_MIN_CONVERSATION_API_STREAMING_URL = "https://api.1min.ai/api/features?isStreaming=true"
ONE_MIN_ASSET_URL = "https://api.1min.ai/api/assets"

# --- Logique des modèles (ton code original) ---
SUBSET_OF_ONE_MIN_PERMITTED_MODELS = ["mistral-nemo", "gpt-4o", "deepseek-chat"]
PERMIT_MODELS_FROM_SUBSET_ONLY = False

# Lecture des variables d'environnement
one_min_models_env = os.getenv("SUBSET_OF_ONE_MIN_PERMITTED_MODELS")
permit_not_in_available_env = os.getenv("PERMIT_MODELS_FROM_SUBSET_ONLY")

if one_min_models_env:
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS = one_min_models_env.split(",")

if permit_not_in_available_env and permit_not_in_available_env.lower() == "true":
    PERMIT_MODELS_FROM_SUBSET_ONLY = True

AVAILABLE_MODELS = []
AVAILABLE_MODELS.extend(SUBSET_OF_ONE_MIN_PERMITTED_MODELS)