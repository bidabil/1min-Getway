# src/infrastructure/circuit_breaker.py
"""
Circuit Breaker Pattern Implementation
Protège l'infrastructure contre les pannes en cascade
"""

import logging
import time
from threading import Lock
from typing import Any

logger = logging.getLogger("1min-gateway.circuit-breaker")


class CircuitBreakerState:
    """États possibles du Circuit Breaker"""

    CLOSED = "closed"  # Fonctionnement normal
    OPEN = "open"  # Bloque les requêtes
    HALF_OPEN = "half_open"  # Test de récupération


class CircuitBreaker:
    """
    Circuit Breaker pour protéger les appels API externes.

    États:
    - CLOSED: Requêtes passent normalement
    - OPEN: Requêtes bloquées immédiatement
    - HALF_OPEN: Une requête de test passe, si succès -> CLOSED, si échec -> OPEN

    Configuration:
    - failure_threshold: Nombre d'échecs avant ouverture (défaut: 5)
    - recovery_timeout: Secondes avant tentative de récupération (défaut: 60)
    - half_open_max_calls: Appels de test en mode half-open (défaut: 1)
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        # État interne
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0
        self._lock = Lock()

        # Métriques
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejected = 0

    @property
    def state(self) -> str:
        """Retourne l'état actuel"""
        with self._lock:
            self._check_recovery()
            return self._state

    @property
    def is_open(self) -> bool:
        """Vérifie si le circuit est ouvert (bloque les requêtes)"""
        with self._lock:
            self._check_recovery()
            return self._state == CircuitBreakerState.OPEN

    @property
    def is_closed(self) -> bool:
        """Vérifie si le circuit est fermé (fonctionnement normal)"""
        return not self.is_open

    def _check_recovery(self) -> None:
        """Vérifie si on peut passer en mode half-open"""
        if (
            self._state == CircuitBreakerState.OPEN
            and self._last_failure_time is not None
            and time.time() - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = CircuitBreakerState.HALF_OPEN
            self._half_open_calls = 0
            logger.info(
                f"🔄 Circuit Breaker [{self.name}]: Passage en HALF_OPEN "
                f"(après {self.recovery_timeout}s)"
            )

    def can_execute(self) -> bool:
        """
        Vérifie si une requête peut être exécutée.
        À appeler AVANT l'appel API.
        """
        with self._lock:
            self._check_recovery()
            self._total_calls += 1

            if self._state == CircuitBreakerState.CLOSED:
                return True

            if self._state == CircuitBreakerState.OPEN:
                self._total_rejected += 1
                logger.warning(f"🚫 Circuit Breaker [{self.name}]: Requête bloquée (OPEN)")
                return False

            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    logger.info(
                        f"🔍 Circuit Breaker [{self.name}]: Test de récupération "
                        f"(appel {self._half_open_calls}/{self.half_open_max_calls})"
                    )
                    return True
                else:
                    self._total_rejected += 1
                    logger.warning(
                        f"🚫 Circuit Breaker [{self.name}]: Requête bloquée (HALF_OPEN, max atteint)"
                    )
                    return False

            return False

    def record_success(self) -> None:
        """Enregistre un succès (à appeler après un appel réussi)"""
        with self._lock:
            self._total_successes += 1

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                # En half-open, un seul succès suffit pour fermer
                self._state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"✅ Circuit Breaker [{self.name}]: Récupéré! Passage en CLOSED")
            elif self._state == CircuitBreakerState.CLOSED:
                # Réinitialise le compteur d'échecs après un succès
                self._failure_count = 0

    def record_failure(self) -> None:
        """Enregistre un échec (à appeler après un appel échoué)"""
        with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitBreakerState.HALF_OPEN:
                # Échec en half-open -> retour à OPEN
                self._state = CircuitBreakerState.OPEN
                self._half_open_calls = 0
                logger.error(
                    f"❌ Circuit Breaker [{self.name}]: Échec en HALF_OPEN, retour en OPEN"
                )
            elif self._state == CircuitBreakerState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitBreakerState.OPEN
                    logger.error(
                        f"⚠️ Circuit Breaker [{self.name}]: OUVERT "
                        f"({self._failure_count} échecs consécutifs, seuil: {self.failure_threshold})"
                    )

    def get_stats(self) -> dict[str, Any]:
        """Retourne les statistiques du circuit breaker"""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "metrics": {
                    "total_calls": self._total_calls,
                    "total_successes": self._total_successes,
                    "total_failures": self._total_failures,
                    "total_rejected": self._total_rejected,
                },
            }

    def reset(self) -> None:
        """Réinitialise le circuit breaker"""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            logger.info(f"🔄 Circuit Breaker [{self.name}]: Réinitialisé")


class CircuitBreakerError(Exception):
    """Exception levée quand le circuit breaker est ouvert"""

    def __init__(self, message: str = "Circuit breaker is open") -> None:
        self.message = message
        super().__init__(self.message)


# Instance globale pour l'API 1min.ai
api_circuit_breaker = CircuitBreaker(
    name="1min-api",
    failure_threshold=5,
    recovery_timeout=60,
    half_open_max_calls=1,
)
