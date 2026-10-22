"""Token estimation for responses whose provider reports no usage (legacy chat API)."""

import math

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))
