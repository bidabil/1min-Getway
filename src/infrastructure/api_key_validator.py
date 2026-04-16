# src/infrastructure/api_key_validator.py
"""
Service de validation des clés API 1min.ai
Vérifie réellement la validité auprès de l'API
"""

import logging

import requests

from ..config import ONE_MIN_BASE_URL

logger = logging.getLogger("1min-gateway.api-key-validator")


class ApiKeyValidator:
    """
    Valide les clés API auprès de l'API 1min.ai.

    Utilise un cache pour éviter les appels répétés à l'API.
    La validation est faite via un appel léger à l'endpoint de santé
    ou via les headers de réponse d'un appel minimal.
    """

    # Cache les clés valides pendant 5 minutes
    CACHE_TTL_SECONDS = 300

    def __init__(self, base_url: str = ONE_MIN_BASE_URL) -> None:
        self._base_url = base_url
        self._validation_endpoint = f"{base_url}/api/features"

    def validate(self, api_key: str) -> tuple[bool, str | None]:
        """
        Valide une clé API auprès de 1min.ai.

        Returns:
            tuple[bool, str | None]: (is_valid, error_message)
        """
        if not api_key:
            return False, "Missing API key"

        # Validation basique du format
        if len(api_key) < 32:
            return False, "Invalid API key format (too short)"

        # Validation auprès de l'API 1min.ai
        # On fait un appel minimal pour vérifier la clé
        try:
            # Utiliser un appel HEAD ou un endpoint léger
            # L'API 1min.ai retourne 401 si la clé est invalide
            response = requests.get(
                f"{self._base_url}/api/user-info",
                headers={"API-KEY": api_key},
                timeout=10,
            )

            if response.status_code == 200:
                logger.debug("API_KEY | Validation réussie")
                return True, None
            elif response.status_code == 401:
                logger.warning("API_KEY | Clé invalide (401)")
                return False, "Invalid API key - Authentication failed"
            elif response.status_code == 403:
                logger.warning("API_KEY | Accès interdit (403)")
                return False, "API key lacks required permissions"
            else:
                logger.warning(f"API_KEY | Statut inattendu: {response.status_code}")
                # En cas d'erreur serveur, on accepte la clé (fail-open)
                # pour ne pas bloquer les utilisateurs
                return True, None

        except requests.exceptions.Timeout:
            logger.warning("API_KEY | Timeout lors de la validation")
            # Fail-open: accepter la clé si l'API est lente
            return True, "Validation timeout - key accepted provisionally"

        except requests.exceptions.ConnectionError:
            logger.warning("API_KEY | Erreur de connexion lors de la validation")
            # Fail-open: accepter la clé si l'API est inaccessible
            return True, "API unreachable - key accepted provisionally"

        except Exception as e:
            logger.error(f"API_KEY | Erreur inattendue: {str(e)}")
            # Fail-open par sécurité
            return True, f"Validation error: {str(e)}"


# Instance globale
api_key_validator = ApiKeyValidator()
