"""
Custom exception classes
"""

from typing import Any, Dict, Optional


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id

    def __str__(self) -> str:
        parts = [f"APIError: {self.message}"]

        if self.code:
            parts.append(f"Code: {self.code}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")

        return " | ".join(parts)


class ValidationError(APIError):
    """Specific error for input validation issues."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        code: Optional[int] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message, code, status_code, details, request_id)
        self.field = field

    def __str__(self) -> str:
        base_str = super().__str__()
        if self.field:
            base_str = base_str.replace(
                "APIError:", f"ValidationError (field: {self.field}):"
            )
        else:
            base_str = base_str.replace("APIError:", "ValidationError:")
        return base_str


class NetworkError(Exception):
    """For network-related issues."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"NetworkError: {self.message} (Caused by: {self.cause})"
        return f"NetworkError: {self.message}"


class WebSocketError(Exception):
    """For WebSocket specific errors."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.session_id = session_id
        self.cause = cause

    def __str__(self) -> str:
        parts = [f"WebSocketError: {self.message}"]

        if self.session_id:
            parts.append(f"Session ID: {self.session_id}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")

        return " | ".join(parts)


class ConfigError(Exception):
    """For configuration loading errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.cause = cause

    def __str__(self) -> str:
        parts = [f"ConfigError: {self.message}"]

        if self.field:
            parts.append(f"Field: {self.field}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")

        return " | ".join(parts)


class AuthenticationError(APIError):
    """Authentication related errors."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, **kwargs)


class AuthorizationError(APIError):
    """Authorization related errors."""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, **kwargs)


class NotFoundError(APIError):
    """Resource not found errors."""

    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(message, **kwargs)


class RateLimitError(APIError):
    """Rate limit exceeded errors."""

    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message, **kwargs)


class ServerError(APIError):
    """Server side errors."""

    def __init__(self, message: str = "Internal server error", **kwargs):
        super().__init__(message, **kwargs)
