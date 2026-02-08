# domain/conversation_service.py

import logging

# Using a generic name for the logger within the service
logger = logging.getLogger("1min-gateway.conversation-service")


def format_conversation_history(messages, new_input):
    """
    Service optimisé pour 1min.ai 2026.
    Retourne UNIQUEMENT le dernier message.
    """
    # Extraction du contenu du dernier message seulement
    clean_input = new_input
    if isinstance(new_input, list):
        # Si c'est un format OpenAI avec images, on extrait juste le texte
        clean_input = " ".join(item["text"] for item in new_input if item.get("type") == "text")

    # LOGIQUE SIMPLIFIÉE : On ne renvoie QUE le nouveau message
    # 1min.ai gère l'historique via conversationId, pas besoin de tout envoyer
    final_prompt = clean_input

    # Log pour debug
    logger.debug(
        f"Service: Prompt envoyé. Longueur: {len(final_prompt)} chars. "
        f"Historique ignoré (géré par 1min.ai via conversationId)."
    )

    return final_prompt
