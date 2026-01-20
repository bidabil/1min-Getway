#model_service.py
import logging

# Standardized logger for the model management layer
logger = logging.getLogger("1min-gateway.model-service")

def get_formatted_models_list(all_models, permit_subset_only, subset_models):
    """
    Constructs the list of available models in OpenAI-compatible format.
    Handles filtering logic based on environment configuration (Full vs. Subset).
    """
    # Determine the source of truth based on user restrictions
    source_list = subset_models if permit_subset_only else all_models
    
    # Safety Check: Warn if the configuration results in an empty list
    if not source_list:
        logger.warning(
            "The models source list is empty! Please check your .env configuration "
            "(SUBSET_OF_ONE_MIN_PERMITTED_MODELS and PERMIT_MODELS_FROM_SUBSET_ONLY)."
        )
    
    # Audit log to monitor which visibility mode is currently active
    mode = "RESTRICTED_SUBSET" if permit_subset_only else "FULL_CATALOG"
    logger.info(f"Model list requested. Mode: {mode}. Returning {len(source_list)} models.")

    # Building the OpenAI structure for each model
    # Note: 'created' timestamp is a placeholder for standard compatibility
    models_data = [
        {
            "id": model_name,
            "object": "model",
            "owned_by": "1min-gateway",
            "created": 1727389042
        }
        for model_name in source_list
    ]
    
    return models_data