"""
Health check service for 1min-Gateway.

Provides comprehensive health checks for:
- API connectivity (1min.ai)
- Circuit breaker status
- Configuration validation
- Optional: Memcached connectivity
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC
from enum import Enum
from typing import Any

import requests

from ..config import (
    APP_ENV,
    AVAILABLE_MODELS,
    MEMCACHED_HOST,
    MEMCACHED_PORT,
    ONE_MIN_AI_API_KEY,
    ONE_MIN_BASE_URL,
)
from .circuit_breaker import api_circuit_breaker as circuit_breaker

logger = logging.getLogger("1min-gateway.health")


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    response_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result: dict[str, Any] = {
            "status": self.status.value,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        if self.response_time_ms is not None:
            result["response_time_ms"] = round(self.response_time_ms, 2)
        return result


@dataclass
class HealthCheckResult:
    """Complete health check result."""

    status: HealthStatus
    version: str = "1.0.0"
    environment: str = "unknown"
    components: list[ComponentHealth] = field(default_factory=list)
    checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "version": self.version,
            "environment": self.environment,
            "checked_at": self.checked_at,
            "components": {comp.name: comp.to_dict() for comp in self.components},
        }


def check_api_connectivity() -> ComponentHealth:
    """
    Check connectivity to 1min.ai API.

    Returns:
        ComponentHealth with status and response time.
    """
    start_time = time.perf_counter()

    try:
        # Use a lightweight endpoint to check connectivity
        # We'll use the user-info endpoint with a short timeout
        response = requests.get(
            f"{ONE_MIN_BASE_URL}/api/user-info",
            headers={"API-KEY": ONE_MIN_AI_API_KEY},
            timeout=5.0,
        )

        response_time = (time.perf_counter() - start_time) * 1000

        if response.status_code == 200:
            return ComponentHealth(
                name="api",
                status=HealthStatus.HEALTHY,
                message="API connectivity OK",
                response_time_ms=response_time,
            )
        elif response.status_code in (401, 403):
            # API is reachable but auth failed - still healthy for connectivity
            return ComponentHealth(
                name="api",
                status=HealthStatus.HEALTHY,
                message="API reachable (auth required)",
                response_time_ms=response_time,
            )
        else:
            return ComponentHealth(
                name="api",
                status=HealthStatus.DEGRADED,
                message=f"API returned status {response.status_code}",
                response_time_ms=response_time,
            )

    except requests.Timeout:
        response_time = (time.perf_counter() - start_time) * 1000
        return ComponentHealth(
            name="api",
            status=HealthStatus.UNHEALTHY,
            message="API timeout (>5s)",
            response_time_ms=response_time,
        )

    except requests.ConnectionError:
        return ComponentHealth(
            name="api",
            status=HealthStatus.UNHEALTHY,
            message="API connection failed",
        )

    except Exception as e:
        logger.exception("Health check failed for API")
        return ComponentHealth(
            name="api",
            status=HealthStatus.UNHEALTHY,
            message=f"API check error: {str(e)}",
        )


def check_circuit_breaker() -> ComponentHealth:
    """
    Check circuit breaker status.

    Returns:
        ComponentHealth with circuit breaker state.
    """
    try:
        stats = circuit_breaker.get_stats()
        state = stats.get("state", "UNKNOWN")

        if state == "CLOSED":
            return ComponentHealth(
                name="circuit_breaker",
                status=HealthStatus.HEALTHY,
                message="Circuit breaker closed (normal operation)",
                details=stats,
            )
        elif state == "HALF_OPEN":
            return ComponentHealth(
                name="circuit_breaker",
                status=HealthStatus.DEGRADED,
                message="Circuit breaker half-open (recovering)",
                details=stats,
            )
        else:  # OPEN
            return ComponentHealth(
                name="circuit_breaker",
                status=HealthStatus.UNHEALTHY,
                message="Circuit breaker open (requests blocked)",
                details=stats,
            )

    except Exception as e:
        logger.exception("Health check failed for circuit breaker")
        return ComponentHealth(
            name="circuit_breaker",
            status=HealthStatus.DEGRADED,
            message=f"Circuit breaker check error: {str(e)}",
        )


def check_configuration() -> ComponentHealth:
    """
    Check configuration validity.

    Returns:
        ComponentHealth with configuration status.
    """
    issues = []

    # Check API key
    if not ONE_MIN_AI_API_KEY:
        issues.append("API key not configured")

    # Check models
    if not AVAILABLE_MODELS:
        issues.append("No models available")

    if issues:
        return ComponentHealth(
            name="configuration",
            status=HealthStatus.DEGRADED,
            message="Configuration issues detected",
            details={"issues": issues},
        )

    return ComponentHealth(
        name="configuration",
        status=HealthStatus.HEALTHY,
        message="Configuration OK",
        details={
            "models_count": len(AVAILABLE_MODELS),
            "environment": APP_ENV,
        },
    )


def check_memcached() -> ComponentHealth:
    """
    Check Memcached connectivity (optional).

    Returns:
        ComponentHealth with Memcached status.
    """
    try:
        import socket

        start_time = time.perf_counter()

        # Try to connect to Memcached
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex((MEMCACHED_HOST, MEMCACHED_PORT))
        sock.close()

        response_time = (time.perf_counter() - start_time) * 1000

        if result == 0:
            return ComponentHealth(
                name="memcached",
                status=HealthStatus.HEALTHY,
                message="Memcached connection OK",
                response_time_ms=response_time,
                details={
                    "host": MEMCACHED_HOST,
                    "port": MEMCACHED_PORT,
                },
            )
        else:
            return ComponentHealth(
                name="memcached",
                status=HealthStatus.DEGRADED,
                message="Memcached not reachable (rate limiting may be affected)",
                details={
                    "host": MEMCACHED_HOST,
                    "port": MEMCACHED_PORT,
                },
            )

    except Exception as e:
        return ComponentHealth(
            name="memcached",
            status=HealthStatus.DEGRADED,
            message=f"Memcached check error: {str(e)}",
        )


def perform_health_check(
    include_api: bool = True,
    include_memcached: bool = True,
) -> HealthCheckResult:
    """
    Perform comprehensive health check.

    Args:
        include_api: Whether to check API connectivity.
        include_memcached: Whether to check Memcached.

    Returns:
        HealthCheckResult with all component statuses.
    """
    from datetime import datetime

    components: list[ComponentHealth] = []

    # Always check circuit breaker and configuration
    components.append(check_circuit_breaker())
    components.append(check_configuration())

    # Optionally check API connectivity
    if include_api:
        components.append(check_api_connectivity())

    # Optionally check Memcached
    if include_memcached:
        components.append(check_memcached())

    # Determine overall status
    statuses = [comp.status for comp in components]

    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY

    return HealthCheckResult(
        status=overall_status,
        environment=APP_ENV,
        components=components,
        checked_at=datetime.now(UTC).isoformat(),
    )


def get_health_status_code(result: HealthCheckResult) -> int:
    """
    Get HTTP status code for health check result.

    Args:
        result: Health check result.

    Returns:
        HTTP status code (200, 503, or 429).
    """
    if result.status == HealthStatus.HEALTHY:
        return 200
    elif result.status == HealthStatus.DEGRADED:
        return 200  # Still return 200 but with degraded status
    else:
        return 503  # Service Unavailable
