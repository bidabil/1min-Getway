# infrastructure/token_service.py

import tiktoken
import logging
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.protocol.instruct.messages import UserMessage

# Using a specific namespace for easier log filtering
logger = logging.getLogger("1min-gateway.token-service")

def calculate_token(sentence, model="gpt-4o"):
    """
    Calculates the number of tokens in a string based on the target model.
    Supports Mistral/Nemo, OpenAI families, and provides approximations for Anthropic.
    """
    if not sentence:
        return 0

    try:
        model_lower = model.lower()

        # --- MISTRAL FAMILY ---
        # Mistral uses a specific tokenizer (Llama 3 based or Tekken)
        if "mistral" in model_lower or "nemo" in model_lower:
            target_model = "open-mistral-nemo" 
            tokenizer = MistralTokenizer.from_model(target_model)
            tokenized = tokenizer.encode_chat_completion(
                ChatCompletionRequest(
                    messages=[UserMessage(content=str(sentence))],
                    model=target_model,
                )
            )
            return len(tokenized.tokens)

        # --- OPENAI & ANTHROPIC FAMILY ---
        # Note: Claude 3 uses a tokenizer similar to cl100k_base or o200k_base.
        # tiktoken is the most reliable tool for these estimates.
        elif any(m in model_lower for m in ["gpt-3.5", "gpt-4", "gpt-4o", "claude", "o1", "o3"]):
            try:
                # Attempt to get the exact encoding for the model
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback to cl100k_base, the most common standard for modern LLMs
                encoding = tiktoken.get_encoding("cl100k_base")
            
            return len(encoding.encode(str(sentence)))

        # --- DEFAULT FALLBACK ---
        # If the model is unknown, we use the standard cl100k_base encoder
        else:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(str(sentence)))
            
    except Exception as e:
        logger.error(f"TOKEN_CALC_ERROR | Model: {model} | Error: {str(e)[:100]}")
        # Fallback estimation: roughly 1 token per 4 characters
        return max(1, len(str(sentence)) // 4)