"""
Token calculation service for 1min-Gateway.
Supports multiple model families with proper encoding.
"""

import logging

import tiktoken
from mistral_common.protocol.instruct.messages import UserMessage
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer

logger = logging.getLogger("1min-gateway.token-service")


def calculate_token(sentence, model="gpt-4o"):
    """
    Calculate tokens based on model family.

    Args:
        sentence: Text to tokenize
        model: Target model name

    Returns:
        int: Estimated token count
    """
    if not sentence:
        return 0

    text = str(sentence)

    try:
        model_lower = model.lower()

        # --- ANTHROPIC CLAUDE MODELS ---
        # Claude has specific tokenization (approximation)
        if any(claude in model_lower for claude in ["claude", "sonnet", "opus", "haiku"]):
            # Claude models use a different tokenizer
            # Approximation: 1 token ≈ 3.5 characters for Claude
            token_count = max(1, len(text) // 3)
            logger.debug(f"TOKEN | Claude model {model}: {token_count} tokens")
            return token_count

        # --- MISTRAL FAMILY ---
        if any(mistral in model_lower for mistral in ["mistral", "nemo", "magistral", "ministral"]):
            try:
                target_model = "open-mistral-nemo"
                tokenizer = MistralTokenizer.from_model(target_model)
                tokenized = tokenizer.encode_chat_completion(
                    ChatCompletionRequest(
                        messages=[UserMessage(content=text)],
                        model=target_model,
                    )
                )
                token_count = len(tokenized.tokens)
                logger.debug(f"TOKEN | Mistral model {model}: {token_count} tokens")
                return token_count
            except Exception as e:
                logger.warning(f"TOKEN | Fallback for Mistral: {str(e)}")
                # Fallback to cl100k_base
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))

        # --- OPENAI & OTHERS ---
        # Try to get exact encoding for the model
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base (used by GPT-4, Claude, Gemini)
            encoding = tiktoken.get_encoding("cl100k_base")

        token_count = len(encoding.encode(text))
        logger.debug(f"TOKEN | {model}: {token_count} tokens")
        return token_count

    except Exception as e:
        logger.error(f"TOKEN | Error for {model}: {str(e)[:100]}")
        # Safe fallback: standard OpenAI approximation
        return max(1, len(text) // 4)
