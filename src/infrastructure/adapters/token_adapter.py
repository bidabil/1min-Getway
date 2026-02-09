# ============================================================================
# src/infrastructure/adapters/token_adapter.py
# ============================================================================
from ...domain.ports import TokenServicePort


class TiktokenAdapter(TokenServicePort):
    """Implémentation du calcul de tokens avec tiktoken"""

    def calculate(self, text: str, model: str) -> int:
        from ..token_service import calculate_token

        return calculate_token(text, model)
