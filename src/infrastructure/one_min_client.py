"""Client API pour 1min.ai avec résilience intégrée.

Ce module gère :
- La création de conversations avec l'API 1min.ai.
- La résilience via un Circuit Breaker et des politiques de Retry.
- La sécurité des logs (masquage des données sensibles).
- La validation stricte des réponses (Content-Type et format JSON).
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
logger = logging.getLogger("1min-gateway.one-min-client")
API_TIMEOUT = 20  # secondes


def get_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
) -> requests.Session:
    """Crée une session requests avec une stratégie de retry automatique."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["POST", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class CircuitBreaker:
    """Implémentation d'un circuit breaker pour protéger l'infrastructure."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """Initialise le circuit breaker avec les seuils configurés.

        Args:
            failure_threshold: Nombre d'échecs consécutifs avant ouverture
            timeout: Durée (secondes) pendant laquelle le circuit reste ouvert
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.opened_at: Optional[float] = None

    def call_failed(self):
        """Enregistre un échec et ouvre le circuit si le seuil est atteint."""
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.time()
            logger.error(
                "⚠️ CIRCUIT BREAKER OUVERT | %d échecs consécutifs. Pause de %ds.",
                self.failures,
                self.timeout,
            )

    def call_succeeded(self):
        """Réinitialise les compteurs suite à un succès."""
        if self.failures > 0:
            logger.info("✅ Circuit Breaker réinitialisé après succès.")
        self.failures = 0
        self.opened_at = None

    def is_open(self) -> bool:
        """Vérifie si le circuit est actuellement ouvert."""
        if self.opened_at is None:
            return False
        if time.time() - self.opened_at > self.timeout:
            logger.info("🔄 Circuit Breaker: Tentative de réouverture (Half-Open)...")
            self.opened_at = None
            self.failures = 0
            return False
        return True


# --- INSTANCES GLOBALES ---
_session = get_retry_session()
_circuit_breaker = CircuitBreaker()


# --- HELPERS INTERNES ---


def _get_safe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Masque les clés sensibles du payload pour le logging debug."""
    sensitive_keys = {"API-KEY", "TOKEN", "AUTHORIZATION", "PASSWORD"}
    return {k: ("[REDACTED]" if k.upper() in sensitive_keys else v) for k, v in payload.items()}


def _handle_response_errors(response: requests.Response) -> bool:
    """Analyse les erreurs HTTP et met à jour l'état du système."""
    if response.status_code in (200, 201):
        return True

    error_messages = {
        400: f"Requête invalide (400). Détails: {response.text[:100]}",
        401: "Authentification échouée (401). Vérifiez votre API-KEY.",
        429: "Rate limit dépassé (429). Trop de requêtes.",
        502: "Bad Gateway (502). L'API 1min.ai est instable.",
        503: "Service Unavailable (503). L'API est en maintenance.",
        504: "Gateway Timeout (504). L'API ne répond pas.",
    }

    msg = error_messages.get(response.status_code, f"Erreur API ({response.status_code})")
    logger.error("INFRA | %s", msg)
    _circuit_breaker.call_failed()
    return False


def _prepare_conversation_request(
    api_key: str,
    model: str,
    conv_type: str,
    title: str,
    file_ids: Optional[List[str]],
    youtube_url: Optional[str],
    prompt_object: Optional[Dict[str, Any]],
) -> tuple[str, Dict[str, Any], Dict[str, str]]:
    """Prépare l'URL, les headers et le payload pour la requête."""
    url = "https://api.1min.ai/api/conversations"

    headers = {
        "API-KEY": api_key,
        "Content-Type": "application/json",
        "User-Agent": "1min-Gateway/1.0",
    }

    payload = {
        "type": conv_type,
        "title": title[:90],
        "model": model,
        "promptObject": prompt_object,
        "fileList": file_ids,
        "youtubeUrl": youtube_url,
    }

    # Nettoyage des champs vides
    clean_payload = {k: v for k, v in payload.items() if v is not None}

    return url, clean_payload, headers


def _process_api_response(response: requests.Response, start_time: float) -> Optional[str]:
    """Traite la réponse de l'API et extrait l'UUID."""

    # 1. Validation HTTP de base
    if not _handle_response_errors(response):
        return None

    # 2. Validation Format
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        logger.error("INFRA | Format de réponse invalide (non-JSON): %s", content_type)
        _circuit_breaker.call_failed()
        return None

    # 3. Parsing JSON sécurisé
    try:
        data = response.json()
    except ValueError as parse_err:
        logger.error("INFRA | Échec du parsing JSON: %s", str(parse_err))
        _circuit_breaker.call_failed()
        return None

    # 4. Extraction de l'UUID
    uuid = data.get("conversation", {}).get("uuid")
    if not uuid:
        logger.error("INFRA | UUID absent de la réponse réussie.")
        _circuit_breaker.call_failed()
        return None

    # Succès
    _circuit_breaker.call_succeeded()
    elapsed = time.time() - start_time
    logger.info("✅ INFRA | Conversation créée: %s (%.2fs)", uuid, elapsed)

    return uuid


# --- FONCTION PRINCIPALE ---


def create_1min_conversation(
    api_key: str,
    model: str,
    conv_type: str = "CHAT_WITH_AI",
    title: str = "n8n Session",
    file_ids: Optional[List[str]] = None,
    youtube_url: Optional[str] = None,
    prompt_object: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Crée une conversation sur l'API 1min.ai et retourne l'UUID de session.

    Args:
        api_key: Clé secrète 1min.ai.
        model: Identifiant du modèle (ex: gpt-4o-mini).
        conv_type: Type de conversation.
        title: Titre de la session (tronqué à 90 chars).
        file_ids: Liste optionnelle d'IDs de fichiers.
        youtube_url: URL optionnelle pour analyse vidéo.
        prompt_object: Configuration spécifique du prompt.

    Returns:
        L'UUID de la conversation créée ou None en cas d'erreur gérée.
    """

    # 1. Vérification circuit breaker
    if _circuit_breaker.is_open():
        logger.error("❌ Circuit Breaker OUVERT. Requête annulée pour protéger le système.")
        raise ConnectionError("Circuit breaker is open - API 1min.ai unavailable")

    try:
        # 2. Préparation
        url, payload, headers = _prepare_conversation_request(
            api_key, model, conv_type, title, file_ids, youtube_url, prompt_object
        )

        # 3. Logging debug
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("INFRA | Envoi Payload: %s", _get_safe_payload(payload))

        # 4. Envoi requête
        start_time = time.time()
        response = _session.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)

        # 5. Traitement réponse
        return _process_api_response(response, start_time)

    except requests.exceptions.Timeout:
        logger.error("TIMEOUT | L'API n'a pas répondu dans le délai de %ds.", API_TIMEOUT)
        _circuit_breaker.call_failed()
        raise

    except requests.exceptions.RequestException as net_err:
        logger.error("NETWORK_ERROR | Erreur de connexion : %s", str(net_err))
        _circuit_breaker.call_failed()
        return None

    except Exception as fatal_err:
        logger.error("FATAL_ERROR | Erreur inattendue : %s", str(fatal_err))
        _circuit_breaker.call_failed()
        return None
