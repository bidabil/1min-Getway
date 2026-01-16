def get_formatted_models_list(all_models, permit_subset_only, subset_models):
    """
    Construit la liste des modèles au format OpenAI.
    Gère la logique de filtrage (Full list vs Subset).
    """
    # On décide quelle liste utiliser selon tes réglages
    if not permit_subset_only:
        source_list = all_models
    else:
        source_list = subset_models
    
    # On génère la structure de données pour chaque modèle
    models_data = [
        {
            "id": model_name,
            "object": "model",
            "owned_by": "1minai",
            "created": 1727389042
        }
        for model_name in source_list
    ]
    
    return models_data