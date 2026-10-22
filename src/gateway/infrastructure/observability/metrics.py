"""Prometheus metrics, kept in a per-application registry."""

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

from ...domain.chat import Usage


class GatewayMetrics:
    content_type = CONTENT_TYPE_LATEST

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.http_requests = Counter(
            "gateway_http_requests_total",
            "HTTP requests handled by the gateway.",
            ["method", "route", "status"],
            registry=self.registry,
        )
        self.http_duration = Histogram(
            "gateway_http_request_duration_seconds",
            "Time to the end of the HTTP response (streams included).",
            ["method", "route"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
            registry=self.registry,
        )
        self.chat_requests = Counter(
            "gateway_chat_requests_total",
            "Chat completions by backend and outcome.",
            ["backend", "api", "outcome"],
            registry=self.registry,
        )
        self.tokens = Counter(
            "gateway_tokens_total",
            "Tokens reported by 1min.ai (or estimated for the legacy API).",
            ["direction", "estimated"],
            registry=self.registry,
        )

    def observe_http(self, method: str, route: str, status: int, seconds: float) -> None:
        self.http_requests.labels(method, route, str(status)).inc()
        self.http_duration.labels(method, route).observe(seconds)

    def observe_chat(self, backend: str, api: str, outcome: str, usage: Usage | None) -> None:
        self.chat_requests.labels(backend, api, outcome).inc()
        if usage is not None:
            estimated = "true" if usage.estimated else "false"
            self.tokens.labels("prompt", estimated).inc(usage.prompt_tokens)
            self.tokens.labels("completion", estimated).inc(usage.completion_tokens)

    def render(self) -> bytes:
        return generate_latest(self.registry)
