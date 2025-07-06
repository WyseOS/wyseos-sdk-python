"""
Custom exception classes for the Wyse Mate Python SDK.

This module defines custom exception classes and utilities for handling API errors.
"""

from typing import Any, Dict, Optional

import requests


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
        """
        Initialize API error.

        Args:
            message: Error message
            code: API error code
            status_code: HTTP status code
            details: Additional error details
            request_id: Request ID for debugging
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id

    def __str__(self) -> str:
        """String representation of the error."""
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
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            code: API error code
            status_code: HTTP status code
            details: Additional error details
            request_id: Request ID for debugging
        """
        super().__init__(message, code, status_code, details, request_id)
        self.field = field

    def __str__(self) -> str:
        """String representation of the validation error."""
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
        """
        Initialize network error.

        Args:
            message: Error message
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        """String representation of the network error."""
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
        """
        Initialize WebSocket error.

        Args:
            message: Error message
            session_id: Session ID related to the error
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.session_id = session_id
        self.cause = cause

    def __str__(self) -> str:
        """String representation of the WebSocket error."""
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
        """
        Initialize configuration error.

        Args:
            message: Error message
            field: Configuration field that caused the error
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.field = field
        self.cause = cause

    def __str__(self) -> str:
        """String representation of the configuration error."""
        parts = [f"ConfigError: {self.message}"]

        if self.field:
            parts.append(f"Field: {self.field}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")

        return " | ".join(parts)


# Specific Error Types
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


def _handle_api_error(response: requests.Response) -> None:
    """
    Parse an HTTP response and raise the appropriate exception.

    Args:
        response: HTTP response object

    Raises:
        APIError: Appropriate API error based on status code and response body
    """
    status_code = response.status_code
    request_id = response.headers.get("X-Request-ID")

    try:
        # Try to parse JSON error response
        error_data = response.json()
        message = error_data.get("msg", "Unknown error")
        code = error_data.get("code")
        details = error_data.get("details", {})

    except (ValueError, KeyError):
        # Fallback to generic error message if JSON parsing fails
        message = f"HTTP {status_code}: {response.reason}"
        code = None
        details = {}

    # Create specific error types based on status code
    if status_code == 400:
        # Check if it's a validation error
        if "validation" in message.lower() or "invalid" in message.lower():
            field = details.get("field")
            raise ValidationError(
                message=message,
                field=field,
                code=code,
                status_code=status_code,
                details=details,
                request_id=request_id,
            )
        else:
            raise APIError(
                message=message,
                code=code,
                status_code=status_code,
                details=details,
                request_id=request_id,
            )

    elif status_code == 401:
        raise AuthenticationError(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            request_id=request_id,
        )

    elif status_code == 403:
        raise AuthorizationError(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            request_id=request_id,
        )

    elif status_code == 404:
        raise NotFoundError(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            request_id=request_id,
        )

    elif status_code == 429:
        raise RateLimitError(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            request_id=request_id,
        )

    elif status_code >= 500:
        raise ServerError(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            request_id=request_id,
        )

    else:
        # Generic API error for other status codes
        raise APIError(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            request_id=request_id,
        )
