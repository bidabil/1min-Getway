"""
Tests for health_service.py module.

Tests cover:
- HealthStatus enum
- ComponentHealth dataclass
- HealthCheckResult dataclass
- check_api_connectivity()
- check_circuit_breaker()
- check_configuration()
- perform_health_check()
- get_health_status_code()
"""

from unittest.mock import MagicMock, patch

import requests

from src.infrastructure.health_service import (
    ComponentHealth,
    HealthCheckResult,
    HealthStatus,
    check_api_connectivity,
    check_circuit_breaker,
    check_configuration,
    get_health_status_code,
    perform_health_check,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """Test that HealthStatus has correct values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_health_status_is_string_enum(self):
        """Test that HealthStatus is a string enum."""
        assert isinstance(HealthStatus.HEALTHY, str)
        assert isinstance(HealthStatus.DEGRADED, str)
        assert isinstance(HealthStatus.UNHEALTHY, str)


class TestComponentHealth:
    """Tests for ComponentHealth dataclass."""

    def test_component_health_creation_minimal(self):
        """Test creating ComponentHealth with minimal fields."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
        )
        assert health.name == "test"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == ""
        assert health.details == {}
        assert health.response_time_ms is None

    def test_component_health_creation_full(self):
        """Test creating ComponentHealth with all fields."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.DEGRADED,
            message="Test message",
            details={"key": "value"},
            response_time_ms=123.45,
        )
        assert health.name == "test"
        assert health.status == HealthStatus.DEGRADED
        assert health.message == "Test message"
        assert health.details == {"key": "value"}
        assert health.response_time_ms == 123.45

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
        )
        result = health.to_dict()
        assert result == {
            "status": "healthy",
            "message": "",
        }

    def test_to_dict_with_details(self):
        """Test to_dict with details."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            details={"key": "value"},
        )
        result = health.to_dict()
        assert result["details"] == {"key": "value"}

    def test_to_dict_with_response_time(self):
        """Test to_dict with response time."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            response_time_ms=100.123,
        )
        result = health.to_dict()
        assert result["response_time_ms"] == 100.12  # Rounded to 2 decimals

    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.DEGRADED,
            message="Test",
            details={"count": 5},
            response_time_ms=50.5,
        )
        result = health.to_dict()
        assert result == {
            "status": "degraded",
            "message": "Test",
            "details": {"count": 5},
            "response_time_ms": 50.5,
        }


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_health_check_result_creation_minimal(self):
        """Test creating HealthCheckResult with minimal fields."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
        )
        assert result.status == HealthStatus.HEALTHY
        assert result.version == "1.0.0"
        assert result.environment == "unknown"
        assert result.components == []
        assert result.checked_at == ""

    def test_health_check_result_creation_full(self):
        """Test creating HealthCheckResult with all fields."""
        component = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
        )
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            version="2.0.0",
            environment="production",
            components=[component],
            checked_at="2024-01-01T00:00:00Z",
        )
        assert result.status == HealthStatus.HEALTHY
        assert result.version == "2.0.0"
        assert result.environment == "production"
        assert len(result.components) == 1
        assert result.checked_at == "2024-01-01T00:00:00Z"

    def test_to_dict(self):
        """Test to_dict for HealthCheckResult."""
        component = ComponentHealth(
            name="api",
            status=HealthStatus.HEALTHY,
            message="OK",
        )
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            version="1.0.0",
            environment="test",
            components=[component],
            checked_at="2024-01-01T00:00:00Z",
        )
        data = result.to_dict()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["environment"] == "test"
        assert data["checked_at"] == "2024-01-01T00:00:00Z"
        assert "api" in data["components"]
        assert data["components"]["api"]["status"] == "healthy"

    def test_to_dict_multiple_components(self):
        """Test to_dict with multiple components."""
        comp1 = ComponentHealth(name="api", status=HealthStatus.HEALTHY)
        comp2 = ComponentHealth(name="db", status=HealthStatus.DEGRADED)
        result = HealthCheckResult(
            status=HealthStatus.DEGRADED,
            components=[comp1, comp2],
        )
        data = result.to_dict()
        assert len(data["components"]) == 2
        assert "api" in data["components"]
        assert "db" in data["components"]


class TestCheckApiConnectivity:
    """Tests for check_api_connectivity function."""

    @patch("src.infrastructure.health_service.requests.get")
    @patch("src.infrastructure.health_service.ONE_MIN_BASE_URL", "https://api.1min.ai")
    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "test-key")
    def test_api_connectivity_success(self, mock_get):
        """Test successful API connectivity check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_api_connectivity()

        assert result.name == "api"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "API connectivity OK"
        assert result.response_time_ms is not None
        mock_get.assert_called_once()

    @patch("src.infrastructure.health_service.requests.get")
    @patch("src.infrastructure.health_service.ONE_MIN_BASE_URL", "https://api.1min.ai")
    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "test-key")
    def test_api_connectivity_auth_required(self, mock_get):
        """Test API connectivity with auth error (still healthy)."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = check_api_connectivity()

        assert result.name == "api"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "API reachable (auth required)"

    @patch("src.infrastructure.health_service.requests.get")
    @patch("src.infrastructure.health_service.ONE_MIN_BASE_URL", "https://api.1min.ai")
    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "test-key")
    def test_api_connectivity_forbidden(self, mock_get):
        """Test API connectivity with forbidden (still healthy)."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = check_api_connectivity()

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "API reachable (auth required)"

    @patch("src.infrastructure.health_service.requests.get")
    @patch("src.infrastructure.health_service.ONE_MIN_BASE_URL", "https://api.1min.ai")
    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "test-key")
    def test_api_connectivity_server_error(self, mock_get):
        """Test API connectivity with server error (degraded)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = check_api_connectivity()

        assert result.status == HealthStatus.DEGRADED
        assert "500" in result.message

    @patch("src.infrastructure.health_service.requests.get")
    @patch("src.infrastructure.health_service.ONE_MIN_BASE_URL", "https://api.1min.ai")
    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "test-key")
    def test_api_connectivity_timeout(self, mock_get):
        """Test API connectivity timeout."""
        mock_get.side_effect = requests.Timeout("Connection timeout")

        result = check_api_connectivity()

        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.message.lower()

    @patch("src.infrastructure.health_service.requests.get")
    @patch("src.infrastructure.health_service.ONE_MIN_BASE_URL", "https://api.1min.ai")
    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "test-key")
    def test_api_connectivity_connection_error(self, mock_get):
        """Test API connectivity connection error."""
        mock_get.side_effect = requests.ConnectionError("Connection failed")

        result = check_api_connectivity()

        assert result.status == HealthStatus.UNHEALTHY
        assert "connection" in result.message.lower()

    @patch("src.infrastructure.health_service.requests.get")
    @patch("src.infrastructure.health_service.ONE_MIN_BASE_URL", "https://api.1min.ai")
    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "test-key")
    def test_api_connectivity_unexpected_error(self, mock_get):
        """Test API connectivity with unexpected error."""
        mock_get.side_effect = ValueError("Unexpected error")

        result = check_api_connectivity()

        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.message.lower()


class TestCheckCircuitBreaker:
    """Tests for check_circuit_breaker function."""

    @patch("src.infrastructure.health_service.circuit_breaker")
    def test_circuit_breaker_closed(self, mock_cb):
        """Test circuit breaker in closed state (healthy)."""
        mock_cb.get_stats.return_value = {
            "state": "CLOSED",
            "failure_count": 0,
            "success_count": 100,
        }

        result = check_circuit_breaker()

        assert result.name == "circuit_breaker"
        assert result.status == HealthStatus.HEALTHY
        assert "closed" in result.message.lower()
        assert result.details["state"] == "CLOSED"

    @patch("src.infrastructure.health_service.circuit_breaker")
    def test_circuit_breaker_half_open(self, mock_cb):
        """Test circuit breaker in half-open state (degraded)."""
        mock_cb.get_stats.return_value = {
            "state": "HALF_OPEN",
            "failure_count": 5,
        }

        result = check_circuit_breaker()

        assert result.status == HealthStatus.DEGRADED
        assert "half-open" in result.message.lower()

    @patch("src.infrastructure.health_service.circuit_breaker")
    def test_circuit_breaker_open(self, mock_cb):
        """Test circuit breaker in open state (unhealthy)."""
        mock_cb.get_stats.return_value = {
            "state": "OPEN",
            "failure_count": 10,
        }

        result = check_circuit_breaker()

        assert result.status == HealthStatus.UNHEALTHY
        assert "open" in result.message.lower()

    @patch("src.infrastructure.health_service.circuit_breaker")
    def test_circuit_breaker_error(self, mock_cb):
        """Test circuit breaker check with error."""
        mock_cb.get_stats.side_effect = Exception("CB error")

        result = check_circuit_breaker()

        assert result.status == HealthStatus.DEGRADED
        assert "error" in result.message.lower()


class TestCheckConfiguration:
    """Tests for check_configuration function."""

    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "valid-key")
    @patch("src.infrastructure.health_service.AVAILABLE_MODELS", ["model1", "model2"])
    @patch("src.infrastructure.health_service.APP_ENV", "development")
    def test_configuration_valid(self):
        """Test valid configuration."""
        result = check_configuration()

        assert result.name == "configuration"
        assert result.status == HealthStatus.HEALTHY
        assert result.details["models_count"] == 2

    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "")
    @patch("src.infrastructure.health_service.AVAILABLE_MODELS", ["model1"])
    @patch("src.infrastructure.health_service.APP_ENV", "development")
    def test_configuration_missing_api_key(self):
        """Test configuration with missing API key."""
        result = check_configuration()

        assert result.status == HealthStatus.DEGRADED
        assert "API key not configured" in result.details["issues"]

    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "valid-key")
    @patch("src.infrastructure.health_service.AVAILABLE_MODELS", [])
    @patch("src.infrastructure.health_service.APP_ENV", "development")
    def test_configuration_no_models(self):
        """Test configuration with no models."""
        result = check_configuration()

        assert result.status == HealthStatus.DEGRADED
        assert "No models available" in result.details["issues"]

    @patch("src.infrastructure.health_service.ONE_MIN_AI_API_KEY", "")
    @patch("src.infrastructure.health_service.AVAILABLE_MODELS", [])
    @patch("src.infrastructure.health_service.APP_ENV", "production")
    def test_configuration_multiple_issues(self):
        """Test configuration with multiple issues."""
        result = check_configuration()

        assert result.status == HealthStatus.DEGRADED
        assert len(result.details["issues"]) == 2


class TestPerformHealthCheck:
    """Tests for perform_health_check function."""

    @patch("src.infrastructure.health_service.check_api_connectivity")
    @patch("src.infrastructure.health_service.check_circuit_breaker")
    @patch("src.infrastructure.health_service.check_configuration")
    @patch("src.infrastructure.health_service.APP_ENV", "test")
    def test_perform_health_check_all_healthy(
        self,
        mock_config,
        mock_cb,
        mock_api,
    ):
        """Test health check with all components healthy."""
        mock_cb.return_value = ComponentHealth(
            name="circuit_breaker",
            status=HealthStatus.HEALTHY,
        )
        mock_config.return_value = ComponentHealth(
            name="configuration",
            status=HealthStatus.HEALTHY,
        )
        mock_api.return_value = ComponentHealth(
            name="api",
            status=HealthStatus.HEALTHY,
        )

        result = perform_health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.environment == "test"
        assert len(result.components) == 3
        assert result.checked_at != ""

    @patch("src.infrastructure.health_service.check_api_connectivity")
    @patch("src.infrastructure.health_service.check_circuit_breaker")
    @patch("src.infrastructure.health_service.check_configuration")
    @patch("src.infrastructure.health_service.APP_ENV", "test")
    def test_perform_health_check_one_unhealthy(
        self,
        mock_config,
        mock_cb,
        mock_api,
    ):
        """Test health check with one unhealthy component."""
        mock_cb.return_value = ComponentHealth(
            name="circuit_breaker",
            status=HealthStatus.HEALTHY,
        )
        mock_config.return_value = ComponentHealth(
            name="configuration",
            status=HealthStatus.HEALTHY,
        )
        mock_api.return_value = ComponentHealth(
            name="api",
            status=HealthStatus.UNHEALTHY,
        )

        result = perform_health_check()

        assert result.status == HealthStatus.UNHEALTHY

    @patch("src.infrastructure.health_service.check_api_connectivity")
    @patch("src.infrastructure.health_service.check_circuit_breaker")
    @patch("src.infrastructure.health_service.check_configuration")
    def test_perform_health_check_one_degraded(
        self,
        mock_config,
        mock_cb,
        mock_api,
    ):
        """Test health check with one degraded component."""
        mock_cb.return_value = ComponentHealth(
            name="circuit_breaker",
            status=HealthStatus.HEALTHY,
        )
        mock_config.return_value = ComponentHealth(
            name="configuration",
            status=HealthStatus.DEGRADED,
        )
        mock_api.return_value = ComponentHealth(
            name="api",
            status=HealthStatus.HEALTHY,
        )

        result = perform_health_check()

        assert result.status == HealthStatus.DEGRADED

    @patch("src.infrastructure.health_service.check_circuit_breaker")
    @patch("src.infrastructure.health_service.check_configuration")
    @patch("src.infrastructure.health_service.APP_ENV", "test")
    def test_perform_health_check_skip_api(self, mock_config, mock_cb):
        """Test health check without API check."""
        mock_cb.return_value = ComponentHealth(
            name="circuit_breaker",
            status=HealthStatus.HEALTHY,
        )
        mock_config.return_value = ComponentHealth(
            name="configuration",
            status=HealthStatus.HEALTHY,
        )

        result = perform_health_check(include_api=False)

        assert result.status == HealthStatus.HEALTHY
        assert len(result.components) == 2


class TestGetHealthStatusCode:
    """Tests for get_health_status_code function."""

    def test_status_code_healthy(self):
        """Test status code for healthy result."""
        result = HealthCheckResult(status=HealthStatus.HEALTHY)
        assert get_health_status_code(result) == 200

    def test_status_code_degraded(self):
        """Test status code for degraded result."""
        result = HealthCheckResult(status=HealthStatus.DEGRADED)
        assert get_health_status_code(result) == 200

    def test_status_code_unhealthy(self):
        """Test status code for unhealthy result."""
        result = HealthCheckResult(status=HealthStatus.UNHEALTHY)
        assert get_health_status_code(result) == 503
