# tests/test_infrastructure/test_circuit_breaker.py
"""
Tests pour le Circuit Breaker.
Pattern AAA: Arrange, Act, Assert
"""

import time

from src.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    api_circuit_breaker,
)


class TestCircuitBreakerStates:
    """Tests pour les transitions d'état du Circuit Breaker."""

    def test_initial_state_is_closed(self):
        """Le circuit breaker démarre en état CLOSED."""
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False

    def test_opens_after_failure_threshold(self):
        """Le circuit s'ouvre après le seuil d'échecs."""
        cb = CircuitBreaker(name="test", failure_threshold=3)

        # Enregistrer 3 échecs
        cb.record_failure()
        assert cb.is_open is False  # Pas encore ouvert

        cb.record_failure()
        assert cb.is_open is False  # Toujours pas

        cb.record_failure()
        assert cb.is_open is True  # Maintenant ouvert
        assert cb.state == CircuitBreakerState.OPEN

    def test_transitions_to_half_open_after_timeout(self):
        """Le circuit passe en HALF_OPEN après le timeout."""
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=1)

        # Ouvrir le circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Attendre le timeout
        time.sleep(1.1)

        # Devrait être en half-open
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_to_closed_on_success(self):
        """En HALF_OPEN, un succès ferme le circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=1)

        # Ouvrir le circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Attendre le timeout pour passer en half-open
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Enregistrer un succès
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.is_open is False

    def test_half_open_to_open_on_failure(self):
        """En HALF_OPEN, un échec rouvre le circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=1)

        # Ouvrir le circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Attendre le timeout pour passer en half-open
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Enregistrer un échec
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.is_open is True


class TestCircuitBreakerCanExecute:
    """Tests pour la méthode can_execute."""

    def test_can_execute_when_closed(self):
        """En état CLOSED, can_execute retourne True."""
        cb = CircuitBreaker(name="test")
        assert cb.can_execute() is True

    def test_cannot_execute_when_open(self):
        """En état OPEN, can_execute retourne False."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True
        assert cb.can_execute() is False

    def test_can_execute_once_in_half_open(self):
        """En état HALF_OPEN, un seul appel est autorisé."""
        cb = CircuitBreaker(
            name="test", failure_threshold=2, recovery_timeout=1, half_open_max_calls=1
        )

        # Ouvrir le circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Attendre le timeout
        time.sleep(1.1)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Premier appel autorisé
        assert cb.can_execute() is True

        # Deuxième appel bloqué (max 1)
        assert cb.can_execute() is False


class TestCircuitBreakerMetrics:
    """Tests pour les métriques du Circuit Breaker."""

    def test_records_total_calls(self):
        """can_execute incrémente le compteur total d'appels."""
        cb = CircuitBreaker(name="test")

        cb.can_execute()
        cb.can_execute()
        cb.can_execute()

        stats = cb.get_stats()
        assert stats["metrics"]["total_calls"] == 3

    def test_records_successes(self):
        """record_success incrémente le compteur de succès."""
        cb = CircuitBreaker(name="test")

        cb.can_execute()
        cb.record_success()
        cb.record_success()

        stats = cb.get_stats()
        assert stats["metrics"]["total_successes"] == 2

    def test_records_failures(self):
        """record_failure incrémente le compteur d'échecs."""
        cb = CircuitBreaker(name="test")

        cb.record_failure()
        cb.record_failure()

        stats = cb.get_stats()
        assert stats["metrics"]["total_failures"] == 2

    def test_records_rejected_calls(self):
        """Les appels bloqués sont comptabilisés."""
        cb = CircuitBreaker(name="test", failure_threshold=1)

        # Ouvrir le circuit
        cb.record_failure()
        assert cb.is_open is True

        # Tenter d'exécuter (bloqué)
        cb.can_execute()
        cb.can_execute()

        stats = cb.get_stats()
        assert stats["metrics"]["total_rejected"] == 2


class TestCircuitBreakerReset:
    """Tests pour la réinitialisation du Circuit Breaker."""

    def test_reset_clears_state(self):
        """reset() remet le circuit en état CLOSED."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        # Ouvrir le circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Reset
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.is_open is False
        assert cb.is_closed is True

    def test_reset_clears_counters(self):
        """reset() remet à zéro les compteurs."""
        cb = CircuitBreaker(name="test")

        cb.record_failure()
        cb.record_failure()
        cb.reset()

        stats = cb.get_stats()
        assert stats["failure_count"] == 0


class TestGlobalCircuitBreaker:
    """Tests pour l'instance globale api_circuit_breaker."""

    def test_global_instance_exists(self):
        """L'instance globale existe et est configurée."""
        assert api_circuit_breaker is not None
        assert api_circuit_breaker.name == "1min-api"

    def test_global_instance_configuration(self):
        """L'instance globale a la bonne configuration."""
        assert api_circuit_breaker.failure_threshold == 5
        assert api_circuit_breaker.recovery_timeout == 60

    def test_global_instance_can_be_reset(self):
        """L'instance globale peut être réinitialisée."""
        # Forcer quelques échecs
        api_circuit_breaker.record_failure()
        api_circuit_breaker.record_failure()

        # Reset
        api_circuit_breaker.reset()
        assert api_circuit_breaker.is_closed is True


class TestCircuitBreakerThreadSafety:
    """Tests pour la thread-safety du Circuit Breaker."""

    def test_concurrent_failures(self):
        """Test de concurrence pour les échecs."""
        import threading

        cb = CircuitBreaker(name="test", failure_threshold=100)
        errors = []

        def record_failures():
            for _ in range(100):
                try:
                    cb.record_failure()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=record_failures) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = cb.get_stats()
        assert stats["metrics"]["total_failures"] == 1000

    def test_concurrent_can_execute(self):
        """Test de concurrence pour can_execute."""
        import threading

        cb = CircuitBreaker(name="test")
        results = []

        def try_execute():
            results.append(cb.can_execute())

        threads = [threading.Thread(target=try_execute) for _ in range(100)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Tous devraient réussir car le circuit est fermé
        assert all(results)


class TestCircuitBreakerStats:
    """Tests pour les statistiques."""

    def test_get_stats_returns_complete_info(self):
        """get_stats retourne toutes les informations."""
        cb = CircuitBreaker(name="test-stats", failure_threshold=3, recovery_timeout=30)

        cb.can_execute()
        cb.record_success()
        cb.record_failure()

        stats = cb.get_stats()

        assert stats["name"] == "test-stats"
        assert stats["state"] == CircuitBreakerState.CLOSED
        assert stats["failure_count"] == 1
        assert stats["failure_threshold"] == 3
        assert stats["recovery_timeout"] == 30
        assert stats["metrics"]["total_calls"] == 1
        assert stats["metrics"]["total_successes"] == 1
        assert stats["metrics"]["total_failures"] == 1
        assert stats["metrics"]["total_rejected"] == 0
