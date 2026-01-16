# Standard Flask tools for easy access via the 'src' package
from flask import request, jsonify, make_response, Response

# Core application factory
from .factory import create_app

# Centralized configuration
from .config import (
    AVAILABLE_MODELS, 
    ONE_MIN_API_URL, 
    ONE_MIN_CONVERSATION_API_URL,
    ONE_MIN_CONVERSATION_API_STREAMING_URL,
    ONE_MIN_ASSET_URL,
    PERMIT_MODELS_FROM_SUBSET_ONLY,
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS
)

# --- Infrastructure layer imports ---
from .infrastructure.token_service import calculate_token
from .infrastructure.error_service import get_error_response
from .infrastructure.asset_service import upload_image_to_1min
from .infrastructure.network_service import handle_options_request, set_response_headers

# --- Domain layer imports ---
from .domain.conversation_service import format_conversation_history
from .domain.model_service import get_formatted_models_list
from .domain.image_service import format_image_generation_response
from .domain.openai_adapter import transform_response, stream_response
from .domain.models import (
    ALL_ONE_MIN_AVAILABLE_MODELS, 
    VISION_SUPPORTED_MODELS, 
    IMAGE_GENERATION_MODELS
)

# Initialize the Flask application, Logger and Rate Limiter
# Important: This must happen AFTER all imports to avoid circular dependencies
app, logger, limiter = create_app()