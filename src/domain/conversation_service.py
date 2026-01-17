import logging

# Using a generic name for the logger within the service
logger = logging.getLogger("1min-gateway.conversation-service")

def format_conversation_history(messages, new_input):
    """
    Service logic to format conversation history into a structured prompt 
    compatible with 1min.ai's text-based completion requirements.
    """
    formatted_history = ["### CONVERSATION HISTORY"]
    
    for message in messages:
        # Standardizing roles for the AI engine
        role = message.get('role', 'user').upper()
        content = message.get('content', '')
        
        # Extract text content if it's a multimodal/list format
        if isinstance(content, list):
            content = ' '.join(item['text'] for item in content if 'text' in item)
        
        formatted_history.append(f"{role}: {content}")
    
    # Process current user input
    clean_input = new_input
    if isinstance(new_input, list):
        clean_input = ' '.join(item['text'] for item in new_input if 'text' in item)

    # Clearly define the context vs. the immediate instruction
    formatted_history.append("\n### CURRENT TASK")
    formatted_history.append(f"USER: {clean_input}")
    formatted_history.append("ASSISTANT: ")

    final_prompt = '\n'.join(formatted_history)
    
    # Traceability: Log the prompt size for cost and limit monitoring
    logger.debug(f"Service: Conversation prompt generated ({len(final_prompt)} chars)")
    
    return final_prompt