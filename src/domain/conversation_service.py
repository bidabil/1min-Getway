def format_conversation_history(messages, new_input):
    """
    Formate l'historique pour 1min.ai.
    """
    formatted_history = ["Conversation History:\n"]
    
    for message in messages:
        role = message.get('role', '').capitalize()
        content = message.get('content', '')
        
        if isinstance(content, list):
            content = '\n'.join(item['text'] for item in content if 'text' in item)
        
        formatted_history.append(f"{role}: {content}")
    
    if messages:
        formatted_history.append("Respond like normal. The conversation history will be automatically updated on the next MESSAGE. DO NOT ADD User: or Assistant: to your output. Just respond like normal.")
        formatted_history.append("User Message:\n")
        
    formatted_history.append(new_input) 
    
    return '\n'.join(formatted_history)