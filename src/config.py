import os
import logging
from dotenv import load_dotenv
from .domain.models import ALL_ONE_MIN_AVAILABLE_MODELS

logger = logging.getLogger("1min-gateway.config")
load_dotenv()

# --- API Endpoints & Constants (STRICT 2026 ALIGNMENT) ---
# Unified features endpoint
ONE_MIN_API_URL = os.getenv("ONE_MIN_API_URL", "https://api.1min.ai/api/features")

# Asset management endpoint
ONE_MIN_ASSET_URL = os.getenv("ONE_MIN_ASSET_URL", "https://api.1min.ai/api/assets")

# URL for streaming specifically (constructed from the base as per doc)
ONE_MIN_CONVERSATION_API_STREAMING_URL = f"{ONE_MIN_API_URL}?isStreaming=true"

ONE_MIN_CONVERSATION_URL = "https://api.1min.ai/api/conversations"

# --- Model Filtering Logic ---

env_subset = os.getenv("SUBSET_OF_ONE_MIN_PERMITTED_MODELS")
if env_subset:
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS = [
        m.strip() for m in env_subset.split(",") if m.strip()
    ]
else:
    # Updated default subset for 2026
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS = ["open-mistral-nemo", "gpt-4o", "deepseek-chat"]

env_permit_only = os.getenv("PERMIT_MODELS_FROM_SUBSET_ONLY", "False")
PERMIT_MODELS_FROM_SUBSET_ONLY = env_permit_only.lower() == "true"

if PERMIT_MODELS_FROM_SUBSET_ONLY:
    AVAILABLE_MODELS = SUBSET_OF_ONE_MIN_PERMITTED_MODELS
    mode_str = "RESTRICTED (Subset only)"
else:
    AVAILABLE_MODELS = ALL_ONE_MIN_AVAILABLE_MODELS
    mode_str = "FULL (All 1min.ai models)"

logger.info(f"Configuration loaded: {len(AVAILABLE_MODELS)} models currently active.")
logger.info(f"Gateway Operating Mode: {mode_str}")