""" Configuration centralisée, typée et validée pour la Gateway 1min.ai."""

import logging
import os
import re
from typing import Final, List, Set

from dotenv import load_dotenv

# Initialisation du logging
logger = logging.getLogger("1min-gateway.config")
load_dotenv()


class Defaults:
    """Valeurs par défaut et constantes de référence."""

    PORT: Final[int] = 5001
    HOST: Final[str] = "0.0.0.0"
    LOG_LEVEL: Final[str] = "INFO"
    APP_ENV: Final[str] = "production"
    BASE_URL: Final[str] = "https://api.1min.ai"

    # Modèles par défaut si la config est erronée
    MODELS: Final[List[str]] = ["gpt-4o-mini", "open-mistral-nemo"]

    # Référence complète des modèles supportés (évite les imports circulaires)
    SUPPORTED_MODELS: Final[List[str]] = [
        "gpt-4o-mini",
        "gpt-4o",
        "claude-3-haiku",
        "claude-3-5-sonnet",
        "gemini-1.5-flash",
        "open-mistral-nemo",
        "deepseek-chat",
    ]

    TRUTHY_VALUES: Final[Set[str]] = {"true", "1", "yes", "on", "enabled"}
    LOG_LEVELS: Final[Set[str]] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


# --- UTILITAIRES DE VALIDATION TYPÉS ---


def get_bool(key: str, default: str = "false") -> bool:
    """Convertit une variable d'environnement en booléen."""
    return os.getenv(key, default).lower() in Defaults.TRUTHY_VALUES


def get_validated_port() -> int:
    """Récupère et valide le port réseau (1-65535)."""
    port_str = os.getenv("PORT", str(Defaults.PORT))
    try:
        port = int(port_str)
        if 1 <= port <= 65535:
            return port
        logger.warning("Port %d hors limites. Utilisation du défaut: %d", port, Defaults.PORT)
    except ValueError:
        logger.warning("Port invalide '%s'. Utilisation du défaut: %d", port_str, Defaults.PORT)
    return Defaults.PORT


def validate_url(url: str, name: str) -> str:
    """Valide le format d'une URL via Regex."""
    pattern = r"^https?://[a-zA-Z0-9.-]+(?::\d+)?"
    if not re.match(pattern, url):
        logger.warning("URL %s malformée: %s. Utilisation du défaut.", name, url)
        return Defaults.BASE_URL
    return url


# --- CHARGEMENT DE LA CONFIGURATION ---

APP_ENV: Final[str] = os.getenv("APP_ENV", Defaults.APP_ENV)
DEBUG: Final[bool] = get_bool("DEBUG", "false")
APP_HOST: Final[str] = os.getenv("HOST", Defaults.HOST)
APP_PORT: Final[int] = get_validated_port()

# Validation des URLs
ONE_MIN_BASE_URL: Final[str] = validate_url(
    os.getenv("ONE_MIN_BASE_URL", Defaults.BASE_URL), "BASE_URL"
)
ONE_MIN_API_URL: Final[str] = f"{ONE_MIN_BASE_URL}/api/features"
ONE_MIN_ASSET_URL: Final[str] = f"{ONE_MIN_BASE_URL}/api/assets"
ONE_MIN_CONVERSATION_URL: Final[str] = f"{ONE_MIN_BASE_URL}/api/conversations"

# --- LOGIQUE DES MODÈLES ---


def load_available_models() -> List[str]:
    """Détermine les modèles disponibles avec validation de cohérence."""
    is_restricted = get_bool("PERMIT_MODELS_FROM_SUBSET_ONLY", "false")
    if not is_restricted:
        return Defaults.SUPPORTED_MODELS

    raw_list = os.getenv("SUBSET_OF_ONE_MIN_PERMITTED_MODELS", "")
    subset = [m.strip() for m in raw_list.split(",") if m.strip()]
    valid_subset = [m for m in subset if m in Defaults.SUPPORTED_MODELS]

    return valid_subset if valid_subset else Defaults.MODELS


AVAILABLE_MODELS: Final[List[str]] = load_available_models()

# --- VALIDATION FINALE DE COHÉRENCE ---


def check_config_safety() -> None:
    """Vérifie les configurations potentiellement dangereuses."""
    if DEBUG and APP_ENV == "production":
        logger.warning("⚠️ SÉCURITÉ | DEBUG=True détecté en production !")
    if not AVAILABLE_MODELS:
        logger.error("❌ CONFIG | Aucun modèle disponible pour la Gateway.")
        raise ValueError("Configuration des modèles vide.")


check_config_safety()

# --- RÉSUMÉ ---


def print_summary() -> None:
    """Affiche un résumé propre au démarrage."""
    summary = {
        "ENV": APP_ENV,
        "PORT": APP_PORT,
        "DEBUG": DEBUG,
        "MODELS": len(AVAILABLE_MODELS),
        "LOG": os.getenv("LOG_LEVEL", Defaults.LOG_LEVEL).upper(),
    }
    logger.info("=" * 40)
    logger.info("🚀 GATEWAY CONFIG LOADED")
    for key, val in summary.items():
        logger.info("%-10s: %s", key, val)
    logger.info("=" * 40)


print_summary()
