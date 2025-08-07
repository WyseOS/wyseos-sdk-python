"""
Wyse Mate Python SDK
"""

__version__ = "0.1.1"
__author__ = "Wyse"
__email__ = "info@wyseos.com"

# Import main classes for easy access
from .client import Client
from .config import ClientOptions
from .errors import APIError, ConfigError, NetworkError, ValidationError, WebSocketError

__all__ = [
    "Client",
    "ClientOptions",
    "APIError",
    "ValidationError",
    "NetworkError",
    "WebSocketError",
    "ConfigError",
]
