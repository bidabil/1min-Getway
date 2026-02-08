# src/__init__.py - REMPLACEZ par :

# Exports de config seulement (pas d'app !)
from .adapters.openai_adapter import stream_response, transform_response
from .config import (
    AVAILABLE_MODELS,
    ONE_MIN_ASSET_API_URL,
    ONE_MIN_CONVERSATION_API_URL,
    ONE_MIN_FEATURE_API_URL,
    PERMIT_MODELS_FROM_SUBSET_ONLY,
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS,
)
from .domain.conversation_service import format_conversation_history
from .domain.model_provider import get_formatted_models_list
from .infrastructure.asset_service import upload_image_to_1min
from .infrastructure.error_service import get_error_response
from .infrastructure.network_service import handle_options_request, set_response_headers

# Exports des services (optionnels)
from .infrastructure.token_service import calculate_token
