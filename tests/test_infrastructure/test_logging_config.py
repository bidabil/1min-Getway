"""
Tests for logging_config.py module.

Tests cover:
- JSONFormatter class
- StructuredLogger class
- setup_logging function
- get_logger function
- RequestLogger context manager
"""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.logging_config import (
    JSONFormatter,
    RequestLogger,
    StructuredLogger,
    get_logger,
    setup_logging,
)


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_format_basic(self):
        """Test basic log formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert "location" in data
        assert data["location"]["file"] == "test.py"
        assert data["location"]["line"] == 42

    def test_format_with_extra(self):
        """Test formatting with extra fields."""
        formatter = JSONFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"
        record.request_id = "abc-123"

        result = formatter.format(record)
        data = json.loads(result)

        assert "extra" in data
        assert data["extra"]["custom_field"] == "custom_value"
        assert data["extra"]["request_id"] == "abc-123"

    def test_format_without_extra(self):
        """Test formatting without extra fields."""
        formatter = JSONFormatter(include_extra=False)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"

        result = formatter.format(record)
        data = json.loads(result)

        assert "extra" not in data

    def test_format_with_exception(self):
        """Test formatting with exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Test error"
        assert "traceback" in data["exception"]

    def test_format_with_stack_info(self):
        """Test formatting with stack info."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.stack_info = "Stack trace here"

        result = formatter.format(record)
        data = json.loads(result)

        assert "stack_trace" in data

    def test_format_different_levels(self):
        """Test formatting different log levels."""
        formatter = JSONFormatter()

        for level, name in [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]:
            record = logging.LogRecord(
                name="test.logger",
                level=level,
                pathname="test.py",
                lineno=42,
                msg=f"{name} message",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert data["level"] == name


class TestStructuredLogger:
    """Tests for StructuredLogger class."""

    def test_logger_creation(self):
        """Test logger creation."""
        logger = StructuredLogger("test.logger")
        assert logger._logger.name == "test.logger"

    def test_debug_logging(self):
        """Test debug logging."""
        logger = StructuredLogger("test.logger")

        with patch.object(logger._logger, "log") as mock_log:
            logger.debug("Debug message", key="value")

            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.DEBUG
            assert args[0][1] == "Debug message"
            assert args[1]["extra"] == {"key": "value"}

    def test_info_logging(self):
        """Test info logging."""
        logger = StructuredLogger("test.logger")

        with patch.object(logger._logger, "log") as mock_log:
            logger.info("Info message", key="value")

            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.INFO

    def test_warning_logging(self):
        """Test warning logging."""
        logger = StructuredLogger("test.logger")

        with patch.object(logger._logger, "log") as mock_log:
            logger.warning("Warning message", key="value")

            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.WARNING

    def test_error_logging(self):
        """Test error logging."""
        logger = StructuredLogger("test.logger")

        with patch.object(logger._logger, "log") as mock_log:
            logger.error("Error message", key="value")

            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.ERROR

    def test_critical_logging(self):
        """Test critical logging."""
        logger = StructuredLogger("test.logger")

        with patch.object(logger._logger, "log") as mock_log:
            logger.critical("Critical message", key="value")

            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.CRITICAL

    def test_exception_logging(self):
        """Test exception logging."""
        logger = StructuredLogger("test.logger")

        with patch.object(logger._logger, "exception") as mock_exc:
            logger.exception("Exception occurred", key="value")

            mock_exc.assert_called_once()
            args = mock_exc.call_args
            assert args[0][0] == "Exception occurred"
            assert args[1]["extra"] == {"key": "value"}

    def test_multiple_extra_fields(self):
        """Test logging with multiple extra fields."""
        logger = StructuredLogger("test.logger")

        with patch.object(logger._logger, "log") as mock_log:
            logger.info(
                "Message",
                key1="value1",
                key2="value2",
                key3=123,
            )

            args = mock_log.call_args
            assert args[1]["extra"] == {
                "key1": "value1",
                "key2": "value2",
                "key3": 123,
            }


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_default(self):
        """Test default logging setup."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            setup_logging()

            assert len(root_logger.handlers) == 1
            handler = root_logger.handlers[0]
            assert isinstance(handler, logging.StreamHandler)
            assert isinstance(handler.formatter, JSONFormatter)
        finally:
            # Restore original handlers
            root_logger.handlers = original_handlers

    def test_setup_custom_level(self):
        """Test setup with custom log level."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            setup_logging(level="DEBUG")

            assert root_logger.level == logging.DEBUG
        finally:
            root_logger.handlers = original_handlers

    def test_setup_plain_text_format(self):
        """Test setup with plain text format."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            setup_logging(json_format=False)

            handler = root_logger.handlers[0]
            assert isinstance(handler.formatter, logging.Formatter)
            assert not isinstance(handler.formatter, JSONFormatter)
        finally:
            root_logger.handlers = original_handlers

    def test_setup_without_extra(self):
        """Test setup without extra fields."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            setup_logging(include_extra=False)

            handler = root_logger.handlers[0]
            assert isinstance(handler.formatter, JSONFormatter)
            assert handler.formatter.include_extra is False
        finally:
            root_logger.handlers = original_handlers

    def test_setup_reduces_third_party_noise(self):
        """Test that third-party loggers are set to WARNING."""
        setup_logging()

        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_structured_logger(self):
        """Test that get_logger returns StructuredLogger."""
        logger = get_logger("test.module")

        assert isinstance(logger, StructuredLogger)
        assert logger._logger.name == "test.module"

    def test_get_logger_different_names(self):
        """Test getting loggers with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1._logger.name == "module1"
        assert logger2._logger.name == "module2"


class TestRequestLogger:
    """Tests for RequestLogger context manager."""

    def test_context_manager_success(self):
        """Test RequestLogger with successful operation."""
        mock_logger = MagicMock(spec=StructuredLogger)
        mock_logger._logger = MagicMock()

        with RequestLogger(mock_logger, "POST /v1/chat", "req-123") as req_log:
            req_log.add_field("model", "gpt-4")
            req_log.add_field("tokens", 100)

        # Should log debug on start
        mock_logger.debug.assert_called()
        # Should log info on completion
        mock_logger.info.assert_called()

        # Check completion call
        info_call = mock_logger.info.call_args
        assert "Completed: POST /v1/chat" in info_call[0][0]
        assert info_call[1]["request_id"] == "req-123"
        assert info_call[1]["model"] == "gpt-4"
        assert info_call[1]["tokens"] == 100
        assert "duration_ms" in info_call[1]

    def test_context_manager_with_exception(self):
        """Test RequestLogger with exception."""
        mock_logger = MagicMock(spec=StructuredLogger)
        mock_logger._logger = MagicMock()

        def _run():
            with RequestLogger(mock_logger, "POST /v1/chat", "req-123"):
                raise ValueError("Test error")

        with pytest.raises(ValueError):
            _run()

        # Should log error on failure
        mock_logger.error.assert_called()

        error_call = mock_logger.error.call_args
        assert "Failed: POST /v1/chat" in error_call[0][0]
        assert error_call[1]["error_type"] == "ValueError"
        assert error_call[1]["error_message"] == "Test error"

    def test_context_manager_without_request_id(self):
        """Test RequestLogger without request ID."""
        mock_logger = MagicMock(spec=StructuredLogger)
        mock_logger._logger = MagicMock()

        with RequestLogger(mock_logger, "GET /health"):
            pass

        # Should work without request_id
        info_call = mock_logger.info.call_args
        assert info_call[1]["request_id"] is None

    def test_add_field(self):
        """Test add_field method."""
        mock_logger = MagicMock(spec=StructuredLogger)
        mock_logger._logger = MagicMock()

        req_log = RequestLogger(mock_logger, "test")
        req_log.add_field("key", "value")

        assert req_log.fields["key"] == "value"

    def test_add_fields(self):
        """Test add_fields method."""
        mock_logger = MagicMock(spec=StructuredLogger)
        mock_logger._logger = MagicMock()

        req_log = RequestLogger(mock_logger, "test")
        req_log.add_fields({"key1": "value1", "key2": "value2"})

        assert req_log.fields["key1"] == "value1"
        assert req_log.fields["key2"] == "value2"

    def test_timing(self):
        """Test that duration is calculated."""
        import time

        mock_logger = MagicMock(spec=StructuredLogger)
        mock_logger._logger = MagicMock()

        with RequestLogger(mock_logger, "test"):
            time.sleep(0.01)  # 10ms

        info_call = mock_logger.info.call_args
        duration = info_call[1]["duration_ms"]
        assert duration > 0

    def test_multiple_add_field_calls(self):
        """Test multiple add_field calls."""
        mock_logger = MagicMock(spec=StructuredLogger)
        mock_logger._logger = MagicMock()

        with RequestLogger(mock_logger, "test") as req_log:
            req_log.add_field("field1", 1)
            req_log.add_field("field2", 2)
            req_log.add_field("field3", 3)

        info_call = mock_logger.info.call_args
        assert info_call[1]["field1"] == 1
        assert info_call[1]["field2"] == 2
        assert info_call[1]["field3"] == 3
