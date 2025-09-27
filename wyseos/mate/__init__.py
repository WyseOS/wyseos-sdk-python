"""
WyseOS Mate Python SDK
"""

__version__ = "0.2.0"
__author__ = "Wyse"
__email__ = "info@wyseos.com"

# Import main classes for easy access
from .client import Client
from .config import ClientOptions
from .errors import APIError, ConfigError, NetworkError, ValidationError, WebSocketError
from .factory import create_task_runner

__all__ = [
    "Client",
    "ClientOptions",
    "APIError",
    "ValidationError",
    "NetworkError",
    "WebSocketError",
    "ConfigError",
    "create_task_runner",
]
