"""
Prometheus metrics for 1min-Gateway.

Exposes metrics at /metrics endpoint for Prometheus scraping.
Includes request counters, histograms, and gauges.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger("1min-gateway.metrics")

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class MetricValue:
    """A single metric value with labels."""

    value: float
    labels: dict[str, str]


class Counter:
    """
    A counter metric that only increases.

    Use for: Request counts, error counts, completed tasks
    """

    def __init__(self, name: str, description: str, label_names: list[str] | None = None):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self._values: dict[tuple[tuple[str, str], ...], float] = {}

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        """Increment the counter by amount."""
        label_key = tuple(sorted(labels.items()))
        self._values[label_key] = self._values.get(label_key, 0) + amount

    def get_values(self) -> list[MetricValue]:
        """Get all values with their labels."""
        return [
            MetricValue(value=value, labels=dict(label_key))
            for label_key, value in self._values.items()
        ]

    def export(self) -> str:
        """Export in Prometheus text format."""
        lines = [f"# HELP {self.name} {self.description}"]
        lines.append(f"# TYPE {self.name} counter")

        for label_key, value in self._values.items():
            if label_key:
                label_str = ",".join(f'{k}="{v}"' for k, v in label_key)
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")

        return "\n".join(lines)


class Gauge:
    """
    A gauge metric that can increase or decrease.

    Use for: Current connections, queue size, memory usage
    """

    def __init__(self, name: str, description: str, label_names: list[str] | None = None):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self._values: dict[tuple[tuple[str, str], ...], float] = {}

    def set(self, value: float, **labels: str) -> None:
        """Set the gauge to a specific value."""
        label_key = tuple(sorted(labels.items()))
        self._values[label_key] = value

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        """Increment the gauge by amount."""
        label_key = tuple(sorted(labels.items()))
        self._values[label_key] = self._values.get(label_key, 0) + amount

    def dec(self, amount: float = 1.0, **labels: str) -> None:
        """Decrement the gauge by amount."""
        label_key = tuple(sorted(labels.items()))
        self._values[label_key] = self._values.get(label_key, 0) - amount

    def get_values(self) -> list[MetricValue]:
        """Get all values with their labels."""
        return [
            MetricValue(value=value, labels=dict(label_key))
            for label_key, value in self._values.items()
        ]

    def export(self) -> str:
        """Export in Prometheus text format."""
        lines = [f"# HELP {self.name} {self.description}"]
        lines.append(f"# TYPE {self.name} gauge")

        for label_key, value in self._values.items():
            if label_key:
                label_str = ",".join(f'{k}="{v}"' for k, v in label_key)
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")

        return "\n".join(lines)


class Histogram:
    """
    A histogram metric for observing distributions.

    Use for: Request duration, response sizes
    """

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(
        self,
        name: str,
        description: str,
        buckets: list[float] | None = None,
        label_names: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self.label_names = label_names or []
        self._counts: dict[tuple[tuple[str, str], ...], dict[float, int]] = {}
        self._sums: dict[tuple[tuple[str, str], ...], float] = {}

    def observe(self, value: float, **labels: str) -> None:
        """Observe a value."""
        label_key = tuple(sorted(labels.items()))

        if label_key not in self._counts:
            self._counts[label_key] = {bucket: 0 for bucket in self.buckets}
            self._sums[label_key] = 0.0

        for bucket in self.buckets:
            if value <= bucket:
                self._counts[label_key][bucket] += 1

        self._sums[label_key] += value

    def get_values(self) -> list[dict[str, Any]]:
        """Get all bucket values."""
        result = []
        for label_key, counts in self._counts.items():
            result.append(
                {
                    "labels": dict(label_key),
                    "buckets": counts,
                    "sum": self._sums[label_key],
                }
            )
        return result

    def export(self) -> str:
        """Export in Prometheus text format."""
        lines = [f"# HELP {self.name} {self.description}"]
        lines.append(f"# TYPE {self.name} histogram")

        for label_key, counts in self._counts.items():
            label_str = ",".join(f'{k}="{v}"' for k, v in label_key) if label_key else ""
            label_prefix = f"{{{label_str}," if label_str else "{"

            cumulative = 0
            for bucket in self.buckets:
                cumulative += counts[bucket]
                bucket_label = f'{label_prefix}le="{bucket}"}}'
                lines.append(f"{self.name}_bucket{bucket_label} {cumulative}")

            # +Inf bucket
            inf_label = f'{label_prefix}le="+Inf"}}'
            lines.append(f"{self.name}_bucket{inf_label} {cumulative}")

            # Sum and count
            if label_str:
                lines.append(f"{self.name}_sum{{{label_str}}} {self._sums[label_key]}")
                lines.append(f"{self.name}_count{{{label_str}}} {cumulative}")
            else:
                lines.append(f"{self.name}_sum {self._sums[label_key]}")
                lines.append(f"{self.name}_count {cumulative}")

        return "\n".join(lines)


class MetricsRegistry:
    """
    Registry for all metrics.

    Manages metric collection and export.
    """

    def __init__(self, namespace: str = "gateway"):
        self.namespace = namespace
        self._metrics: dict[str, Counter | Gauge | Histogram] = {}

    def register(self, metric: Counter | Gauge | Histogram) -> None:
        """Register a metric."""
        full_name = f"{self.namespace}_{metric.name}"
        metric.name = full_name
        self._metrics[metric.name] = metric

    def counter(self, name: str, description: str, label_names: list[str] | None = None) -> Counter:
        """Create and register a counter."""
        counter = Counter(name, description, label_names)
        self.register(counter)
        return counter

    def gauge(self, name: str, description: str, label_names: list[str] | None = None) -> Gauge:
        """Create and register a gauge."""
        gauge = Gauge(name, description, label_names)
        self.register(gauge)
        return gauge

    def histogram(
        self,
        name: str,
        description: str,
        buckets: list[float] | None = None,
        label_names: list[str] | None = None,
    ) -> Histogram:
        """Create and register a histogram."""
        histogram = Histogram(name, description, buckets, label_names)
        self.register(histogram)
        return histogram

    def export(self) -> str:
        """Export all metrics in Prometheus text format."""
        return "\n\n".join(metric.export() for metric in self._metrics.values())

    def get_metrics(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        return {
            name: {
                "type": type(metric).__name__,
                "values": metric.get_values() if hasattr(metric, "get_values") else None,
            }
            for name, metric in self._metrics.items()
        }


# Global metrics registry
metrics = MetricsRegistry(namespace="one_min_gateway")

# Pre-defined metrics
REQUEST_COUNT = metrics.counter(
    "http_requests_total",
    "Total number of HTTP requests",
    label_names=["method", "endpoint", "status"],
)

REQUEST_DURATION = metrics.histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    label_names=["method", "endpoint"],
)

ACTIVE_REQUESTS = metrics.gauge(
    "active_requests",
    "Number of active requests",
)

CIRCUIT_BREAKER_STATE = metrics.gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    label_names=["name"],
)

CIRCUIT_BREAKER_FAILURES = metrics.gauge(
    "circuit_breaker_failures",
    "Number of failures in circuit breaker",
    label_names=["name"],
)

MODEL_REQUESTS = metrics.counter(
    "model_requests_total",
    "Total number of requests per model",
    label_names=["model", "status"],
)

CACHE_HITS = metrics.counter(
    "cache_hits_total",
    "Total number of cache hits",
    label_names=["cache_name"],
)

CACHE_MISSES = metrics.counter(
    "cache_misses_total",
    "Total number of cache misses",
    label_names=["cache_name"],
)


def track_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Track an HTTP request."""
    REQUEST_COUNT.inc(method=method, endpoint=endpoint, status=str(status))
    REQUEST_DURATION.observe(duration, method=method, endpoint=endpoint)


def track_model_request(model: str, status: str) -> None:
    """Track a model request."""
    MODEL_REQUESTS.inc(model=model, status=status)


def update_circuit_breaker_metrics(name: str, state: str, failures: int) -> None:
    """Update circuit breaker metrics."""
    state_values = {"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}
    CIRCUIT_BREAKER_STATE.set(state_values.get(state, -1), name=name)
    CIRCUIT_BREAKER_FAILURES.set(failures, name=name)


def track_cache_hit(cache_name: str) -> None:
    """Track a cache hit."""
    CACHE_HITS.inc(cache_name=cache_name)


def track_cache_miss(cache_name: str) -> None:
    """Track a cache miss."""
    CACHE_MISSES.inc(cache_name=cache_name)


def timed(histogram: Histogram, **labels: str) -> Callable[[F], F]:
    """
    Decorator to time a function and record in histogram.

    Usage:
        @timed(REQUEST_DURATION, method="GET", endpoint="/v1/models")
        async def get_models():
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                histogram.observe(duration, **labels)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                histogram.observe(duration, **labels)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def get_metrics_output() -> str:
    """Get the Prometheus metrics output."""
    return metrics.export()
