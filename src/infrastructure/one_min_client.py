# one_min_client.py
"""
Client API pour 1min.ai
Aligné sur la documentation officielle : https://docs.1min.ai/conversation-api
"""

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("1min-gateway.one-min-client")

# Configuration
API_TIMEOUT = 30
CONVERSATION_API_URL = "https://api.1min.ai/api/conversations"


class CircuitBreaker:
    """Circuit breaker pour protéger l'infrastructure."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.opened_at: float | None = None

    def call_failed(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.time()
            logger.error("⚠️ CIRCUIT BREAKER OUVERT | %d échecs.", self.failures)

    def call_succeeded(self) -> None:
        if self.failures > 0:
            logger.info("✅ Circuit Breaker réinitialisé")
        self.failures = 0
        self.opened_at = None

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.time() - self.opened_at > self.timeout:
            self.opened_at = None
            self.failures = 0
            return False
        return True


def get_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> requests.Session:
    """Crée une session requests avec retry automatique."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["POST", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount(
        "http://",  # nosemgrep: python.lang.security.audit.insecure-transport.requests.request-session-with-http.request-session-with-http
        adapter,
    )
    session.mount("https://", adapter)
    return session


_session = get_retry_session()
_circuit_breaker = CircuitBreaker()


def _get_safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Masque les données sensibles pour le logging"""
    sensitive_keys = {"API-KEY", "TOKEN", "AUTHORIZATION", "PASSWORD"}
    return {k: ("[REDACTED]" if k.upper() in sensitive_keys else v) for k, v in payload.items()}


def create_1min_conversation(
    api_key: str,
    model: str,
    conv_type: str = "CHAT_WITH_AI",
    title: str = "Gateway Session",
    file_ids: list[str] | None = None,
    youtube_url: str | None = None,
) -> str | None:
    """
    Crée une conversation sur l'API 1min.ai.

    Documentation : https://docs.1min.ai/conversation-api

    Required Parameters:
        - type: string (CHAT_WITH_AI, CHAT_WITH_IMAGE, CHAT_WITH_PDF, CHAT_WITH_YOUTUBE_VIDEO)
        - title: string (maximum 91 characters)
        - model: string

    Optional Parameters:
        - fileList: array (required for CHAT_WITH_PDF)
        - youtubeUrl: string (required for CHAT_WITH_YOUTUBE_VIDEO)

    Returns:
        UUID de la conversation ou None en cas d'erreur
    """

    # Vérification du circuit breaker
    if _circuit_breaker.is_open():
        logger.warning("INFRA | Circuit Breaker ouvert. Requête bloquée.")
        return None

    start_time = time.time()

    try:
        # Headers selon documentation officielle
        headers = {
            "API-KEY": api_key,
            "Content-Type": "application/json",
        }

        # Payload selon documentation
        payload: dict[str, Any] = {
            "type": conv_type,
            "title": title[:91],  # Maximum 91 characters selon doc
            "model": model,
        }

        # Paramètres optionnels selon le type de conversation
        if file_ids and conv_type == "CHAT_WITH_PDF":
            payload["fileList"] = file_ids

        if youtube_url and conv_type == "CHAT_WITH_YOUTUBE_VIDEO":
            payload["youtubeUrl"] = youtube_url

        # Log sécurisé
        logger.debug(f"INFRA | POST {CONVERSATION_API_URL}")
        logger.debug(f"INFRA | Payload: {_get_safe_payload(payload)}")

        # Exécution
        response = _session.post(
            CONVERSATION_API_URL,
            json=payload,
            headers=headers,
            timeout=API_TIMEOUT,
        )

        # Gestion des erreurs HTTP
        if response.status_code == 400:
            logger.error(f"INFRA | Bad Request (400): {response.text[:200]}")
            _circuit_breaker.call_failed()
            return None

        if response.status_code == 401:
            logger.error("INFRA | Unauthorized (401): Invalid or missing API key")
            _circuit_breaker.call_failed()
            return None

        if response.status_code == 403:
            logger.error("INFRA | Forbidden (403): Insufficient permissions or quota exceeded")
            _circuit_breaker.call_failed()
            return None

        if response.status_code == 422:
            logger.error(f"INFRA | Unprocessable Entity (422): {response.text[:200]}")
            _circuit_breaker.call_failed()
            return None

        if response.status_code not in (200, 201):
            logger.error(f"INFRA | HTTP {response.status_code}: {response.text[:200]}")
            _circuit_breaker.call_failed()
            return None

        # Validation Content-Type
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            logger.error(f"INFRA | Format invalide (non-JSON): {content_type}")
            _circuit_breaker.call_failed()
            return None

        # Parsing JSON
        try:
            data = response.json()
        except ValueError as parse_err:
            logger.error(f"INFRA | Échec parsing JSON: {str(parse_err)}")
            _circuit_breaker.call_failed()
            return None

        # Extraction UUID selon structure documentée
        # Response: { "conversation": { "uuid": "...", "title": "...", ... } }
        conversation_uuid: str | None = data.get("conversation", {}).get("uuid")

        if not conversation_uuid:
            logger.error(f"INFRA | UUID absent de la réponse: {data}")
            _circuit_breaker.call_failed()
            return None

        # Succès
        _circuit_breaker.call_succeeded()
        elapsed = time.time() - start_time
        logger.info(
            f"✅ INFRA | Conversation créée: {conversation_uuid} "
            f"(Type: {conv_type}, Model: {model}, {elapsed:.2f}s)"
        )

        return conversation_uuid

    except requests.exceptions.Timeout:
        logger.error(f"INFRA | Timeout après {API_TIMEOUT}s")
        _circuit_breaker.call_failed()
        return None

    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"INFRA | Erreur de connexion: {str(conn_err)}")
        _circuit_breaker.call_failed()
        return None

    except requests.exceptions.RequestException as req_err:
        logger.error(f"INFRA | Erreur réseau: {str(req_err)}")
        _circuit_breaker.call_failed()
        return None

    except Exception as e:
        logger.error(f"INFRA | Erreur inattendue: {type(e).__name__}: {str(e)}")
        _circuit_breaker.call_failed()
        return None
