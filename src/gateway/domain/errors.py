"""Domain errors.

Each error carries an ErrorKind; the HTTP layer maps kinds to status codes and to the
wire format of the API family that received the request (OpenAI or Anthropic).
"""

from enum import Enum


class ErrorKind(Enum):
    INVALID_REQUEST = "invalid_request"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    RATE_LIMITED = "rate_limited"
    UPSTREAM = "upstream"
    UPSTREAM_TIMEOUT = "upstream_timeout"
    UNAVAILABLE = "unavailable"
    INTERNAL = "internal"


class GatewayError(Exception):
    kind: ErrorKind = ErrorKind.INTERNAL
    default_code = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        param: str | None = None,
        retry_after: float | None = None,
        upstream_request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.param = param
        self.retry_after = retry_after
        self.upstream_request_id = upstream_request_id


class InvalidRequestError(GatewayError):
    kind = ErrorKind.INVALID_REQUEST
    default_code = "invalid_request"


class AuthenticationError(GatewayError):
    kind = ErrorKind.AUTHENTICATION
    default_code = "invalid_api_key"


class PermissionDeniedError(GatewayError):
    kind = ErrorKind.PERMISSION
    default_code = "permission_denied"


class NotFoundError(GatewayError):
    kind = ErrorKind.NOT_FOUND
    default_code = "not_found"


class PayloadTooLargeError(GatewayError):
    kind = ErrorKind.PAYLOAD_TOO_LARGE
    default_code = "payload_too_large"


class RateLimitError(GatewayError):
    kind = ErrorKind.RATE_LIMITED
    default_code = "rate_limit_exceeded"


class UpstreamError(GatewayError):
    kind = ErrorKind.UPSTREAM
    default_code = "upstream_error"


class UpstreamTimeoutError(GatewayError):
    kind = ErrorKind.UPSTREAM_TIMEOUT
    default_code = "upstream_timeout"


class ServiceUnavailableError(GatewayError):
    kind = ErrorKind.UNAVAILABLE
    default_code = "service_unavailable"
