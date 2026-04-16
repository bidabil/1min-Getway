"""
Webhook system for 1min-Gateway.

Provides event notifications to external services via webhooks.
Supports various event types and retry logic.
"""

import hashlib
import hmac
import json
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests

logger = logging.getLogger("1min-gateway.webhooks")


def _sanitize_for_log(value: Any) -> str:
    """
    Sanitize a value before logging to reduce risk of log injection.

    - Ensures the returned value is always a string.
    - Removes CR, LF and TAB characters to prevent log injection via newlines.
    - Truncates overly long values to avoid log flooding.
    """
    # Convert non-string values to a safe string representation
    if not isinstance(value, str):
        value = repr(value)

    # Remove characters that can break log formatting
    sanitized: str = value.replace("\r", "").replace("\n", "").replace("\t", " ")

    # Limit length to avoid excessively large log entries
    max_length = 500
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "…"

    return sanitized


class WebhookEvent(str, Enum):
    """Types of webhook events."""

    REQUEST_COMPLETED = "request.completed"
    REQUEST_FAILED = "request.failed"
    CIRCUIT_BREAKER_OPENED = "circuit_breaker.opened"
    CIRCUIT_BREAKER_CLOSED = "circuit_breaker.closed"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    MODEL_CHANGED = "model.changed"
    HEALTH_CHECK_FAILED = "health_check.failed"


@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint."""

    url: str
    secret: str
    events: list[WebhookEvent]
    enabled: bool = True
    timeout: int = 10
    max_retries: int = 3
    retry_delay: int = 5


@dataclass
class WebhookPayload:
    """Payload sent to webhook endpoints."""

    event: WebhookEvent
    timestamp: float
    data: dict[str, Any]
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event": self.event.value,
            "timestamp": self.timestamp,
            "data": self.data,
            "signature": self.signature,
        }

    def compute_signature(self, secret: str) -> str:
        """Compute HMAC signature for the payload."""
        payload_str = json.dumps(
            {
                "event": self.event.value,
                "timestamp": self.timestamp,
                "data": self.data,
            },
            sort_keys=True,
        )

        return hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""

    webhook_url: str
    event: WebhookEvent
    success: bool
    status_code: int | None
    error: str | None
    timestamp: float
    retry_count: int = 0


class WebhookManager:
    """
    Manages webhook registrations and deliveries.

    Features:
    - Register/unregister webhooks
    - Event filtering per webhook
    - Async delivery with retries
    - Signature verification
    - Delivery history
    """

    def __init__(self, max_history: int = 100):
        self._webhooks: dict[str, WebhookConfig] = {}
        self._delivery_history: list[WebhookDelivery] = []
        self._max_history = max_history
        self._stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "retries": 0,
        }

    def register(
        self,
        name: str,
        url: str,
        secret: str,
        events: list[WebhookEvent] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Register a new webhook.

        Args:
            name: Unique name for the webhook
            url: Webhook endpoint URL
            secret: Secret for signature verification
            events: List of events to subscribe to (None = all events)
            **kwargs: Additional config options
        """
        config = WebhookConfig(
            url=url,
            secret=secret,
            events=events or list(WebhookEvent),
            enabled=kwargs.get("enabled", True),
            timeout=kwargs.get("timeout", 10),
            max_retries=kwargs.get("max_retries", 3),
            retry_delay=kwargs.get("retry_delay", 5),
        )
        self._webhooks[name] = config
        safe_name = _sanitize_for_log(name)
        safe_url = _sanitize_for_log(url)
        logger.info("Webhook registered: name=%s url=%s", safe_name, safe_url)

    def unregister(self, name: str) -> bool:
        """
        Unregister a webhook.

        Args:
            name: Name of the webhook to remove

        Returns:
            True if removed, False if not found
        """
        if name in self._webhooks:
            del self._webhooks[name]
            safe_name = _sanitize_for_log(name)
            logger.info("Webhook unregistered: name=%s", safe_name)
            return True
        return False

    def trigger(self, event: WebhookEvent, data: dict[str, Any]) -> None:
        """
        Trigger a webhook event.

        Sends to all registered webhooks subscribed to this event.

        Args:
            event: The event type
            data: Event data
        """
        payload = WebhookPayload(
            event=event,
            timestamp=time.time(),
            data=data,
        )

        for name, config in self._webhooks.items():
            if not config.enabled:
                continue

            if event not in config.events:
                continue

            # Send asynchronously
            thread = threading.Thread(
                target=self._deliver,
                args=(name, config, payload),
                daemon=True,
            )
            thread.start()

    def _deliver(
        self,
        name: str,
        config: WebhookConfig,
        payload: WebhookPayload,
    ) -> None:
        """Deliver a webhook payload with retries."""
        payload.signature = payload.compute_signature(config.secret)

        for attempt in range(config.max_retries + 1):
            try:
                response = requests.post(
                    config.url,
                    json=payload.to_dict(),
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Event": payload.event.value,
                        "X-Webhook-Signature": payload.signature,
                    },
                    timeout=config.timeout,
                )

                if response.status_code < 400:
                    self._record_delivery(
                        config.url,
                        payload.event,
                        success=True,
                        status_code=response.status_code,
                        retry_count=attempt,
                    )
                    logger.debug(f"Webhook delivered: {name} -> {config.url}")
                    return

                # Non-2xx response
                if attempt < config.max_retries:
                    self._stats["retries"] += 1
                    time.sleep(config.retry_delay)
                    continue

                self._record_delivery(
                    config.url,
                    payload.event,
                    success=False,
                    status_code=response.status_code,
                    error=f"HTTP {response.status_code}",
                    retry_count=attempt,
                )

            except requests.Timeout:
                if attempt < config.max_retries:
                    self._stats["retries"] += 1
                    time.sleep(config.retry_delay)
                    continue

                self._record_delivery(
                    config.url,
                    payload.event,
                    success=False,
                    error="Timeout",
                    retry_count=attempt,
                )

            except requests.RequestException as e:
                if attempt < config.max_retries:
                    self._stats["retries"] += 1
                    time.sleep(config.retry_delay)
                    continue

                self._record_delivery(
                    config.url,
                    payload.event,
                    success=False,
                    error=str(e),
                    retry_count=attempt,
                )

    def _record_delivery(
        self,
        webhook_url: str,
        event: WebhookEvent,
        success: bool,
        status_code: int | None = None,
        error: str | None = None,
        retry_count: int = 0,
    ) -> None:
        """Record a delivery attempt."""
        self._stats["total_sent"] += 1

        if success:
            self._stats["successful"] += 1
        else:
            self._stats["failed"] += 1

        delivery = WebhookDelivery(
            webhook_url=webhook_url,
            event=event,
            success=success,
            status_code=status_code,
            error=error,
            timestamp=time.time(),
            retry_count=retry_count,
        )

        self._delivery_history.append(delivery)

        # Trim history if needed
        if len(self._delivery_history) > self._max_history:
            self._delivery_history = self._delivery_history[-self._max_history :]

    def get_stats(self) -> dict[str, Any]:
        """Get webhook statistics."""
        return {
            **self._stats,
            "registered_webhooks": len(self._webhooks),
            "enabled_webhooks": sum(1 for w in self._webhooks.values() if w.enabled),
        }

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Get delivery history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of delivery records
        """
        recent = self._delivery_history[-limit:]
        return [
            {
                "webhook_url": d.webhook_url,
                "event": d.event.value,
                "success": d.success,
                "status_code": d.status_code,
                "error": d.error,
                "timestamp": d.timestamp,
                "retry_count": d.retry_count,
            }
            for d in recent
        ]

    def list_webhooks(self) -> list[dict[str, Any]]:
        """List all registered webhooks."""
        return [
            {
                "name": name,
                "url": config.url,
                "enabled": config.enabled,
                "events": [e.value for e in config.events],
            }
            for name, config in self._webhooks.items()
        ]


# Global webhook manager instance
webhook_manager = WebhookManager()
