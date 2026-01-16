
# Import des outils Flask pour qu'ils soient accessibles via 'src'
from flask import request, jsonify, make_response, Response

# Import de la factory
from .factory import create_app

# Dans src/__init__.py, modifie l'import de config :
from .config import (
    AVAILABLE_MODELS, 
    ONE_MIN_API_URL, 
    ONE_MIN_CONVERSATION_API_URL,
    ONE_MIN_CONVERSATION_API_STREAMING_URL,
    ONE_MIN_ASSET_URL,
    PERMIT_MODELS_FROM_SUBSET_ONLY,
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS
)

# Import des services
from .infrastructure.token_service import calculate_token
from .infrastructure.error_handler import ERROR_HANDLER
from .infrastructure.asset_service import upload_image_to_1min
from .infrastructure.network_utils import handle_options_request, set_response_headers


from .domain.conversation_service import format_conversation_history
from .domain.model_service import get_formatted_models_list
from .domain.openai_adapter import transform_response, stream_response
from .domain.models import (
    ALL_ONE_MIN_AVAILABLE_MODELS, 
    vision_supported_models, 
    image_generation_models
)

# On initialise l'app immédiatement pour l'exposer
app, logger, limiter = create_app()

