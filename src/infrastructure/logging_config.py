"""
Structured JSON logging configuration for 1min-Gateway.

Provides JSON-formatted logs for better parsing in monitoring systems
like ELK Stack, Datadog, or Google Cloud Logging.
"""

import json
import logging
import sys
import time
from datetime import UTC, datetime
from typing import Any

from ..config import LOG_LEVEL


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter that outputs log records as JSON.

    Output format:
    {
        "timestamp": "2024-01-15T10:30:00.000Z",
        "level": "INFO",
        "logger": "1min-gateway.api",
        "message": "Request processed",
        "request_id": "abc-123",
        "duration_ms": 150,
        "extra": {...}
    }
    """

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Base log entry
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add location info
        log_entry["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add extra fields from the record
        if self.include_extra:
            extra_fields = {}
            # Standard LogRecord attributes to exclude
            standard_attrs = {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "asctime",
            }

            for key, value in record.__dict__.items():
                if key not in standard_attrs and not key.startswith("_"):
                    extra_fields[key] = value

            if extra_fields:
                log_entry["extra"] = extra_fields

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add stack info if present
        if record.stack_info:
            log_entry["stack_trace"] = self.formatStack(record.stack_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class StructuredLogger:
    """
    A structured logger that provides convenient methods for common logging patterns.

    Usage:
        logger = StructuredLogger("1min-gateway.api")
        logger.info("Request processed", request_id="abc-123", duration_ms=150)
        logger.error("Request failed", error_code=500, reason="timeout")
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal method to log with extra fields."""
        self._logger.log(level, message, extra=kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with optional extra fields."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with optional extra fields."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with optional extra fields."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with optional extra fields."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with optional extra fields."""
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._logger.exception(message, extra=kwargs)


def setup_logging(
    level: str | None = None,
    json_format: bool = True,
    include_extra: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to LOG_LEVEL from config.
        json_format: If True, output JSON format. If False, use plain text.
        include_extra: If True, include extra fields in JSON output.
    """
    log_level = level or LOG_LEVEL

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Set formatter
    if json_format:
        formatter: logging.Formatter = JSONFormatter(include_extra=include_extra)
    else:
        # Plain text format for development
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__).

    Returns:
        StructuredLogger instance.
    """
    return StructuredLogger(name)


class RequestLogger:
    """Context manager for logging HTTP requests with timing."""

    def __init__(
        self,
        logger: StructuredLogger,
        operation: str,
        request_id: str | None = None,
    ):
        self.logger = logger
        self.operation = operation
        self.request_id = request_id
        self.start_time: float | None = None
        self.fields: dict[str, Any] = {}

    def __enter__(self) -> "RequestLogger":
        self.start_time = time.perf_counter()
        self.logger.debug(f"Started: {self.operation}", request_id=self.request_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000 if self.start_time else 0
        if exc_type:
            self.logger.error(
                f"Failed: {self.operation}",
                request_id=self.request_id,
                duration_ms=round(duration_ms, 2),
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.fields,
            )
        else:
            self.logger.info(
                f"Completed: {self.operation}",
                request_id=self.request_id,
                duration_ms=round(duration_ms, 2),
                **self.fields,
            )

    def add_field(self, key: str, value: Any) -> None:
        self.fields[key] = value

    def add_fields(self, fields: dict[str, Any]) -> None:
        self.fields.update(fields)
