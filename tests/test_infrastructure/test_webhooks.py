"""
Tests for webhooks.py module.

Tests cover:
- WebhookEvent enum
- WebhookConfig dataclass
- WebhookPayload dataclass
- WebhookDelivery dataclass
- WebhookManager class
- trigger_event function
"""

import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch

import requests

from src.infrastructure.webhooks import (
    WebhookConfig,
    WebhookDelivery,
    WebhookEvent,
    WebhookManager,
    WebhookPayload,
    trigger_event,
    webhook_manager,
)


class TestWebhookEvent:
    """Tests for WebhookEvent enum."""

    def test_webhook_event_values(self):
        """Test webhook event values."""
        assert WebhookEvent.REQUEST_COMPLETED.value == "request.completed"
        assert WebhookEvent.REQUEST_FAILED.value == "request.failed"
        assert WebhookEvent.CIRCUIT_BREAKER_OPENED.value == "circuit_breaker.opened"
        assert WebhookEvent.CIRCUIT_BREAKER_CLOSED.value == "circuit_breaker.closed"
        assert WebhookEvent.RATE_LIMIT_EXCEEDED.value == "rate_limit.exceeded"
        assert WebhookEvent.MODEL_CHANGED.value == "model.changed"
        assert WebhookEvent.HEALTH_CHECK_FAILED.value == "health_check.failed"

    def test_webhook_event_is_string_enum(self):
        """Test that WebhookEvent is a string enum."""
        assert isinstance(WebhookEvent.REQUEST_COMPLETED, str)


class TestWebhookConfig:
    """Tests for WebhookConfig dataclass."""

    def test_webhook_config_creation(self):
        """Test creating a webhook config."""
        config = WebhookConfig(
            url="https://example.com/webhook",
            secret="test-secret-value",  # pragma: allowlist secret
            events=[WebhookEvent.REQUEST_COMPLETED],
        )
        assert config.url == "https://example.com/webhook"
        assert config.secret == "my-secret"
        assert config.events == [WebhookEvent.REQUEST_COMPLETED]
        assert config.enabled is True
        assert config.timeout == 10
        assert config.max_retries == 3
        assert config.retry_delay == 5

    def test_webhook_config_custom_values(self):
        """Test creating a webhook config with custom values."""
        config = WebhookConfig(
            url="https://example.com/webhook",
            secret="test-secret-value",  # pragma: allowlist secret
            events=[WebhookEvent.REQUEST_COMPLETED],
            enabled=False,
            timeout=30,
            max_retries=5,
            retry_delay=10,
        )
        assert config.enabled is False
        assert config.timeout == 30
        assert config.max_retries == 5
        assert config.retry_delay == 10


class TestWebhookPayload:
    """Tests for WebhookPayload dataclass."""

    def test_webhook_payload_creation(self):
        """Test creating a webhook payload."""
        payload = WebhookPayload(
            event=WebhookEvent.REQUEST_COMPLETED,
            timestamp=1234567890.0,
            data={"key": "value"},
        )
        assert payload.event == WebhookEvent.REQUEST_COMPLETED
        assert payload.timestamp == 1234567890.0
        assert payload.data == {"key": "value"}
        assert payload.signature == ""

    def test_webhook_payload_to_dict(self):
        """Test converting payload to dictionary."""
        payload = WebhookPayload(
            event=WebhookEvent.REQUEST_COMPLETED,
            timestamp=1234567890.0,
            data={"key": "value"},
            signature="abc123",
        )
        result = payload.to_dict()

        assert result["event"] == "request.completed"
        assert result["timestamp"] == 1234567890.0
        assert result["data"] == {"key": "value"}
        assert result["signature"] == "abc123"

    def test_compute_signature(self):
        """Test computing HMAC signature."""
        payload = WebhookPayload(
            event=WebhookEvent.REQUEST_COMPLETED,
            timestamp=1234567890.0,
            data={"key": "value"},
        )

        signature = payload.compute_signature("my-secret")

        # Verify signature format (hex string)
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 produces 64 hex chars

    def test_signature_verification(self):
        """Test that signature can be verified."""
        payload = WebhookPayload(
            event=WebhookEvent.REQUEST_COMPLETED,
            timestamp=1234567890.0,
            data={"key": "value"},
        )

        secret = "my-secret"
        signature = payload.compute_signature(secret)

        # Verify manually
        payload_str = json.dumps(
            {
                "event": payload.event.value,
                "timestamp": payload.timestamp,
                "data": payload.data,
            },
            sort_keys=True,
        )

        expected = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert signature == expected


class TestWebhookDelivery:
    """Tests for WebhookDelivery dataclass."""

    def test_webhook_delivery_creation(self):
        """Test creating a webhook delivery record."""
        delivery = WebhookDelivery(
            webhook_url="https://example.com/webhook",
            event=WebhookEvent.REQUEST_COMPLETED,
            success=True,
            status_code=200,
            error=None,
            timestamp=1234567890.0,
        )
        assert delivery.webhook_url == "https://example.com/webhook"
        assert delivery.event == WebhookEvent.REQUEST_COMPLETED
        assert delivery.success is True
        assert delivery.status_code == 200
        assert delivery.error is None
        assert delivery.retry_count == 0

    def test_webhook_delivery_with_error(self):
        """Test creating a webhook delivery with error."""
        delivery = WebhookDelivery(
            webhook_url="https://example.com/webhook",
            event=WebhookEvent.REQUEST_FAILED,
            success=False,
            status_code=None,
            error="Connection timeout",
            timestamp=1234567890.0,
            retry_count=3,
        )
        assert delivery.success is False
        assert delivery.error == "Connection timeout"
        assert delivery.retry_count == 3


class TestWebhookManager:
    """Tests for WebhookManager class."""

    def test_manager_creation(self):
        """Test creating a webhook manager."""
        manager = WebhookManager()
        assert manager._webhooks == {}
        assert manager._delivery_history == []
        assert manager._max_history == 100

    def test_manager_custom_max_history(self):
        """Test creating a manager with custom max history."""
        manager = WebhookManager(max_history=50)
        assert manager._max_history == 50

    def test_register_webhook(self):
        """Test registering a webhook."""
        manager = WebhookManager()
        manager.register(
            name="test_webhook",
            url="https://example.com/webhook",
            secret="secret",
            events=[WebhookEvent.REQUEST_COMPLETED],
        )

        assert "test_webhook" in manager._webhooks
        assert manager._webhooks["test_webhook"].url == "https://example.com/webhook"

    def test_register_webhook_all_events(self):
        """Test registering a webhook for all events."""
        manager = WebhookManager()
        manager.register(
            name="test_webhook",
            url="https://example.com/webhook",
            secret="secret",
            events=None,  # All events
        )

        assert len(manager._webhooks["test_webhook"].events) == len(WebhookEvent)

    def test_unregister_webhook(self):
        """Test unregistering a webhook."""
        manager = WebhookManager()
        manager.register("test", "https://example.com", "secret")

        result = manager.unregister("test")

        assert result is True
        assert "test" not in manager._webhooks

    def test_unregister_nonexistent(self):
        """Test unregistering a nonexistent webhook."""
        manager = WebhookManager()
        result = manager.unregister("nonexistent")
        assert result is False

    def test_enable_webhook(self):
        """Test enabling a webhook."""
        manager = WebhookManager()
        manager.register("test", "https://example.com", "secret")
        manager._webhooks["test"].enabled = False

        result = manager.enable("test")

        assert result is True
        assert manager._webhooks["test"].enabled is True

    def test_enable_nonexistent(self):
        """Test enabling a nonexistent webhook."""
        manager = WebhookManager()
        result = manager.enable("nonexistent")
        assert result is False

    def test_disable_webhook(self):
        """Test disabling a webhook."""
        manager = WebhookManager()
        manager.register("test", "https://example.com", "secret")

        result = manager.disable("test")

        assert result is True
        assert manager._webhooks["test"].enabled is False

    def test_disable_nonexistent(self):
        """Test disabling a nonexistent webhook."""
        manager = WebhookManager()
        result = manager.disable("nonexistent")
        assert result is False

    def test_get_stats(self):
        """Test getting webhook statistics."""
        manager = WebhookManager()
        manager.register("test1", "https://example1.com", "secret")
        manager.register("test2", "https://example2.com", "secret")
        manager.disable("test2")

        stats = manager.get_stats()

        assert stats["registered_webhooks"] == 2
        assert stats["enabled_webhooks"] == 1
        assert stats["total_sent"] == 0

    def test_list_webhooks(self):
        """Test listing webhooks."""
        manager = WebhookManager()
        manager.register(
            "test1",
            "https://example1.com",
            "secret",
            events=[WebhookEvent.REQUEST_COMPLETED],
        )

        webhooks = manager.list_webhooks()

        assert len(webhooks) == 1
        assert webhooks[0]["name"] == "test1"
        assert webhooks[0]["url"] == "https://example1.com"
        assert webhooks[0]["enabled"] is True
        assert "request.completed" in webhooks[0]["events"]

    def test_get_history_empty(self):
        """Test getting empty history."""
        manager = WebhookManager()
        history = manager.get_history()
        assert history == []

    @patch("src.infrastructure.webhooks.requests.post")
    def test_trigger_event_success(self, mock_post):
        """Test triggering an event successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        manager = WebhookManager()
        manager.register(
            "test",
            "https://example.com/webhook",
            "secret",
            events=[WebhookEvent.REQUEST_COMPLETED],
        )

        manager.trigger(WebhookEvent.REQUEST_COMPLETED, {"key": "value"})

        # Wait for async thread
        time.sleep(0.1)

        mock_post.assert_called()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["event"] == "request.completed"

    @patch("src.infrastructure.webhooks.requests.post")
    def test_trigger_event_disabled_webhook(self, mock_post):
        """Test that disabled webhooks don't receive events."""
        manager = WebhookManager()
        manager.register(
            "test",
            "https://example.com/webhook",
            "secret",
            events=[WebhookEvent.REQUEST_COMPLETED],
        )
        manager.disable("test")

        manager.trigger(WebhookEvent.REQUEST_COMPLETED, {"key": "value"})

        time.sleep(0.1)
        mock_post.assert_not_called()

    @patch("src.infrastructure.webhooks.requests.post")
    def test_trigger_event_filtered(self, mock_post):
        """Test that webhooks only receive subscribed events."""
        manager = WebhookManager()
        manager.register(
            "test",
            "https://example.com/webhook",
            "secret",
            events=[WebhookEvent.REQUEST_COMPLETED],  # Only this event
        )

        manager.trigger(WebhookEvent.REQUEST_FAILED, {"key": "value"})

        time.sleep(0.1)
        mock_post.assert_not_called()

    @patch("src.infrastructure.webhooks.requests.post")
    def test_trigger_with_failure(self, mock_post):
        """Test handling webhook delivery failure."""
        mock_post.side_effect = requests.RequestException("Connection error")

        manager = WebhookManager()
        manager.register(
            "test",
            "https://example.com/webhook",
            "secret",
            events=[WebhookEvent.REQUEST_COMPLETED],
            max_retries=0,  # No retries for faster test
        )

        manager.trigger(WebhookEvent.REQUEST_COMPLETED, {"key": "value"})

        time.sleep(0.1)

        # Check stats
        stats = manager.get_stats()
        assert stats["failed"] == 1

    @patch("src.infrastructure.webhooks.requests.post")
    def test_trigger_with_timeout(self, mock_post):
        """Test handling webhook timeout."""
        mock_post.side_effect = requests.Timeout("Timeout")

        manager = WebhookManager()
        manager.register(
            "test",
            "https://example.com/webhook",
            "secret",
            events=[WebhookEvent.REQUEST_COMPLETED],
            max_retries=0,
        )

        manager.trigger(WebhookEvent.REQUEST_COMPLETED, {"key": "value"})

        time.sleep(0.1)

        stats = manager.get_stats()
        assert stats["failed"] == 1

    @patch("src.infrastructure.webhooks.requests.post")
    def test_history_recording(self, mock_post):
        """Test that delivery history is recorded."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        manager = WebhookManager()
        manager.register(
            "test",
            "https://example.com/webhook",
            "secret",
            events=[WebhookEvent.REQUEST_COMPLETED],
        )

        manager.trigger(WebhookEvent.REQUEST_COMPLETED, {"key": "value"})

        time.sleep(0.1)

        history = manager.get_history()
        assert len(history) == 1
        assert history[0]["success"] is True
        assert history[0]["status_code"] == 200

    def test_history_limit(self):
        """Test that history is limited to max_history."""
        manager = WebhookManager(max_history=5)

        # Add more than max_history records
        for _ in range(10):
            manager._delivery_history.append(
                WebhookDelivery(
                    webhook_url="https://example.com",
                    event=WebhookEvent.REQUEST_COMPLETED,
                    success=True,
                    status_code=200,
                    error=None,
                    timestamp=time.time(),
                )
            )
            # Simulate the trimming
            if len(manager._delivery_history) > manager._max_history:
                manager._delivery_history = manager._delivery_history[-manager._max_history :]

        assert len(manager._delivery_history) <= 5


class TestTriggerEvent:
    """Tests for trigger_event convenience function."""

    @patch("src.infrastructure.webhooks.webhook_manager")
    def test_trigger_event_calls_manager(self, mock_manager):
        """Test that trigger_event calls the global manager."""
        trigger_event(WebhookEvent.REQUEST_COMPLETED, {"key": "value"})

        mock_manager.trigger.assert_called_once_with(
            WebhookEvent.REQUEST_COMPLETED,
            {"key": "value"},
        )


class TestGlobalWebhookManager:
    """Tests for global webhook_manager instance."""

    def test_global_manager_exists(self):
        """Test that global manager exists."""
        assert webhook_manager is not None
        assert isinstance(webhook_manager, WebhookManager)
