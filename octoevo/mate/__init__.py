"""
OctoEvo Python SDK
"""

__version__ = __import__("importlib.metadata", fromlist=["version"]).version("octoevo")
__author__ = "OctoEvo"
__email__ = "info@octoevo.ai"

# Import main classes for easy access
from .client import Client
from .config import ClientOptions
from .errors import APIError, ConfigError, NetworkError, SessionExecutionError, ValidationError, WebSocketError
from .factory import create_task_runner
from .task_runner import ExecutionMode

__all__ = [
    "Client",
    "ClientOptions",
    "APIError",
    "ValidationError",
    "NetworkError",
    "WebSocketError",
    "SessionExecutionError",
    "ConfigError",
    "ExecutionMode",
    "create_task_runner",
]
