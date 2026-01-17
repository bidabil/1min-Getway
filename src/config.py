import os
import logging
from dotenv import load_dotenv
# We import the full list to handle the False case of PERMIT_MODELS_FROM_SUBSET_ONLY
from .domain.models import ALL_ONE_MIN_AVAILABLE_MODELS

# Initializing a local logger for startup diagnostic
logger = logging.getLogger("1min-gateway.config")

# Load environment variables from .env file
load_dotenv()

# --- API Endpoints & Constants ---
ONE_MIN_API_URL = os.getenv("ONE_MIN_API_URL", "https://api.1min.ai/api/features")
ONE_MIN_CONVERSATION_API_URL = os.getenv("ONE_MIN_CONVERSATION_API_URL", "https://api.1min.ai/api/conversations")
ONE_MIN_CONVERSATION_API_STREAMING_URL = os.getenv("ONE_MIN_CONVERSATION_API_STREAMING_URL", "https://api.1min.ai/api/features?isStreaming=true")
ONE_MIN_ASSET_URL = os.getenv("ONE_MIN_ASSET_URL", "https://api.1min.ai/api/assets")

# --- Model Filtering Logic ---

# 1. Processing the Model SUBSET
env_subset = os.getenv("SUBSET_OF_ONE_MIN_PERMITTED_MODELS")
if env_subset:
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS = [
        m.strip() for m in env_subset.split(",") if m.strip()
    ]
else:
    # Default selection if nothing is defined in the .env
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS = ["mistral-nemo", "gpt-4o", "deepseek-chat"]

# 2. Processing the Boolean Filtering Flag
env_permit_only = os.getenv("PERMIT_MODELS_FROM_SUBSET_ONLY", "False")
PERMIT_MODELS_FROM_SUBSET_ONLY = env_permit_only.lower() == "true"

# 3. Final logic to define AVAILABLE_MODELS
# This determines what the gateway actually validates and displays
if PERMIT_MODELS_FROM_SUBSET_ONLY:
    AVAILABLE_MODELS = SUBSET_OF_ONE_MIN_PERMITTED_MODELS
    mode_str = "RESTRICTED (Subset only)"
else:
    AVAILABLE_MODELS = ALL_ONE_MIN_AVAILABLE_MODELS
    mode_str = "FULL (All 1min.ai models)"

# --- Startup Diagnostics ---
logger.info(f"Configuration loaded: {len(AVAILABLE_MODELS)} models currently active.")
logger.info(f"Gateway Operating Mode: {mode_str}")