# src/__init__.py

# 1. Initialisation de l'application via la Factory
from .factory import create_app

app, logger, limiter = create_app()

# 2. Export des utilitaires Flask (utilisés dans main.py)
from flask import Response, jsonify, make_response, request

# 5. Export des Adapters (Transformation OpenAI)
from .adapters.openai_adapter import stream_response, transform_response

# 3. Export de la Configuration
from .config import (
    ALL_ONE_MIN_AVAILABLE_MODELS,
    ONE_MIN_API_URL,
    ONE_MIN_CONVERSATION_API_STREAMING_URL,
    PERMIT_MODELS_FROM_SUBSET_ONLY,
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS,
)

# 6. Export de la Logique Métier (Domaine)
from .domain.conversation_service import format_conversation_history
from .domain.model_provider import get_formatted_models_list
from .infrastructure.asset_service import upload_image_to_1min

# 4. Export des Services d'Infrastructure
from .infrastructure.error_service import get_error_response
from .infrastructure.network_service import handle_options_request, set_response_headers
from .infrastructure.token_service import calculate_token
