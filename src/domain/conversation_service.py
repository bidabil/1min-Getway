# domain/conversation_service.py

import logging

# Using a generic name for the logger within the service
logger = logging.getLogger("1min-gateway.conversation-service")

def format_conversation_history(messages, new_input):
    """
    Service logic optimized for 1min.ai 2026.
    Avoids token redundancy by letting 1min.ai handle history via conversationId.
    """
    
    # 1. Extraction propre du nouveau message (Current Task)
    clean_input = new_input
    if isinstance(new_input, list):
        # On extrait uniquement le texte si c'est un format OpenAI Vision
        clean_input = ' '.join(item['text'] for item in new_input if item.get('type') == 'text')

    # 2. LOGIQUE DE CONTEXTE (Doc 2026) :
    # Si messages est vide, c'est le début d'un chat.
    # Si messages contient des éléments, 1min.ai utilise le conversationId pour l'historique.
    # On évite donc de renvoyer tout l'historique dans le champ 'prompt'.
    
    if not messages:
        # Premier message de la conversation
        final_prompt = clean_input
    else:
        # Pour les messages suivants, on n'envoie que la nouvelle instruction.
        # 1min.ai fera la jointure avec le passé via le conversationId.
        final_prompt = clean_input

    # Traceability
    logger.debug(f"Service: Prompt processed. Length: {len(final_prompt)} chars. History ignored (handled by conversationId).")
    
    return final_prompt