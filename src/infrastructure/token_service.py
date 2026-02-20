"""
Token calculation service for 1min-Gateway.
Supports multiple model families with proper encoding.
"""

import logging
from typing import Any

import tiktoken
from mistral_common.protocol.instruct.messages import UserMessage
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer

logger = logging.getLogger("1min-gateway.token-service")


def _sanitize_for_log(value: Any) -> str:
    """
    Sanitize a value before logging to reduce risk of log injection.

    - Ensures the returned value is always a string.
    - Removes CR, LF and TAB characters to prevent log injection via newlines.
    - Truncates overly long values to avoid log flooding.
    """
    # Convert non-string values to a safe string representation
    if not isinstance(value, str):
        value = repr(value)

    # Remove characters that can break log formatting
    sanitized: str = value.replace("\r", "").replace("\n", "").replace("\t", " ")

    # Limit length to avoid excessively large log entries
    max_length = 100
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "…"

    return sanitized


def calculate_token(sentence: str, model: str = "gpt-4o") -> int:
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
        safe_model = _sanitize_for_log(model)

        # --- ANTHROPIC CLAUDE MODELS ---
        # Claude has specific tokenization (approximation)
        if any(claude in model_lower for claude in ["claude", "sonnet", "opus", "haiku"]):
            # Claude models use a different tokenizer
            # Approximation: 1 token ≈ 3.5 characters for Claude
            token_count = max(1, len(text) // 3)
            logger.debug("TKN | Claude model %s: %d tokens", safe_model, token_count)
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
                logger.debug("TKN | Mistral model %s: %d tokens", safe_model, token_count)
                return token_count
            except Exception as e:
                logger.warning("TKN | Fallback for Mistral: %s", _sanitize_for_log(str(e)))
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
        logger.debug("TKN | %s: %d tokens", safe_model, token_count)
        return token_count

    except Exception as e:
        logger.error("TKN | Error for %s: %s", _sanitize_for_log(model), _sanitize_for_log(str(e)))
        # Safe fallback: standard OpenAI approximation
        return max(1, len(text) // 4)
