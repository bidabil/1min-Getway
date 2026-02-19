# config.py

"""
Configuration centralisée pour la Gateway 1min.AI
Alignée sur la documentation officielle : https://docs.1min.ai
"""

import logging
import os
from typing import Final

from dotenv import load_dotenv

# Import en haut du fichier (E402 fix)
from .domain.models import AVAILABLE_MODELS as ALL_MODELS

logger = logging.getLogger("1min-gateway.config")
load_dotenv()


# ============================================================================
# AUTHENTIFICATION
# ============================================================================
ONE_MIN_AI_API_KEY: Final[str] = os.getenv("ONE_MIN_AI_API_KEY", "")

# ============================================================================
# ENDPOINTS API (selon documentation officielle)
# ============================================================================
ONE_MIN_BASE_URL: Final[str] = os.getenv("ONE_MIN_BASE_URL", "https://api.1min.ai")

# Endpoints dérivés (automatiquement générés)
ONE_MIN_FEATURE_API_URL: Final[str] = f"{ONE_MIN_BASE_URL}/api/features"
ONE_MIN_CONVERSATION_API_URL: Final[str] = f"{ONE_MIN_BASE_URL}/api/conversations"
ONE_MIN_ASSET_API_URL: Final[str] = f"{ONE_MIN_BASE_URL}/api/assets"

# ============================================================================
# CONFIGURATION SERVEUR
# ============================================================================
APP_ENV: Final[str] = os.getenv("APP_ENV", "production")
DEBUG: Final[bool] = os.getenv("DEBUG", "False").lower() == "true"
APP_HOST: Final[str] = os.getenv("HOST", "0.0.0.0")
APP_PORT: Final[int] = int(os.getenv("PORT", "5001"))

# ============================================================================
# MEMCACHED
# ============================================================================
MEMCACHED_HOST: Final[str] = os.getenv("MEMCACHED_HOST", "memcached")
MEMCACHED_PORT: Final[int] = int(os.getenv("MEMCACHED_PORT", "11211"))

# ============================================================================
# MODÈLES DISPONIBLES
# ============================================================================
PERMIT_MODELS_FROM_SUBSET_ONLY: Final[bool] = (
    os.getenv("PERMIT_MODELS_FROM_SUBSET_ONLY", "False").lower() == "true"
)

SUBSET_OF_ONE_MIN_PERMITTED_MODELS: Final[list[str]] = [
    m.strip() for m in os.getenv("SUBSET_OF_ONE_MIN_PERMITTED_MODELS", "").split(",") if m.strip()
]

# Détermination des modèles actifs
AVAILABLE_MODELS: Final[list[str]] = (
    SUBSET_OF_ONE_MIN_PERMITTED_MODELS
    if PERMIT_MODELS_FROM_SUBSET_ONLY and SUBSET_OF_ONE_MIN_PERMITTED_MODELS
    else ALL_MODELS
)

# ============================================================================
# RATE LIMITING (selon documentation : 180 req/min par défaut)
# ============================================================================
RATELIMIT_ENABLED: Final[bool] = os.getenv("RATELIMIT_ENABLED", "True").lower() == "true"
RATELIMIT_STORAGE_URL: Final[str] = os.getenv(
    "RATELIMIT_STORAGE_URL", f"memcache://{MEMCACHED_HOST}:{MEMCACHED_PORT}"
)
RATELIMIT_DEFAULT: Final[str] = os.getenv("RATELIMIT_DEFAULT", "180 per minute")
RATELIMIT_MODELS_LIST: Final[str] = os.getenv("RATELIMIT_MODELS_LIST", "180 per minute")

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: Final[str] = os.getenv("LOG_FILE", "/app/logs/gateway.log")

# ============================================================================
# SÉCURITÉ
# ============================================================================
SECRET_KEY: Final[str] = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
CORS_ORIGINS: Final[str] = os.getenv("CORS_ORIGINS", "*")

# Mode de validation API Key: "fast" (format only) ou "full" (avec vérification API)
API_KEY_VALIDATION_MODE: Final[str] = os.getenv("API_KEY_VALIDATION_MODE", "fast")


# ============================================================================
# VALIDATION DE LA CONFIGURATION
# ============================================================================
def validate_config() -> None:
    """Valide la configuration au démarrage"""
    errors: list[str] = []

    # Vérification de la clé API
    if not ONE_MIN_AI_API_KEY:
        errors.append("❌ ONE_MIN_AI_API_KEY manquante dans .env")

    # Vérification de la sécurité en production
    if APP_ENV == "production":
        if SECRET_KEY == "CHANGE_ME_IN_PRODUCTION":
            errors.append("❌ SECRET_KEY doit être changée en production")
        if DEBUG:
            logger.warning("⚠️ DEBUG=True en production - Non recommandé")

    # Vérification des modèles
    if not AVAILABLE_MODELS:
        errors.append("❌ Aucun modèle disponible - Vérifiez SUBSET_OF_ONE_MIN_PERMITTED_MODELS")

    if errors:
        for error in errors:
            logger.error(error)
        raise ValueError("Configuration invalide - Voir les erreurs ci-dessus")

    logger.info("✅ Configuration validée avec succès")


def print_config_summary() -> None:
    """Affiche un résumé de la configuration au démarrage"""
    mode = "SUBSET" if PERMIT_MODELS_FROM_SUBSET_ONLY else "TOUS"

    logger.info("=" * 60)
    logger.info("🚀 1MIN-GATEWAY - CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Environnement      : {APP_ENV}")
    logger.info(f"Debug              : {DEBUG}")
    logger.info(f"Host:Port          : {APP_HOST}:{APP_PORT}")
    logger.info(f"API Endpoint       : {ONE_MIN_BASE_URL}")
    logger.info(f"Modèles disponibles: {len(AVAILABLE_MODELS)} ({mode})")
    logger.info(f"Rate Limit         : {RATELIMIT_DEFAULT}")
    logger.info(f"Log Level          : {LOG_LEVEL}")
    logger.info("=" * 60)


# Exécution des validations au chargement du module
validate_config()
print_config_summary()
