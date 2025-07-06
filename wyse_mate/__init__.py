"""
Wyse Mate Python SDK

A Python SDK for interacting with the Wyse Mate.
"""

__version__ = "0.1.0"
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
