"""
Configuration management for the Wyse Mate Python SDK.

"""

from pathlib import Path
from typing import Any, Optional, Type, TypeVar

try:
    import yaml
except ImportError:
    raise ImportError(
        "PyYAML is required for configuration file support. "
        "Install it with: pip install pyyaml"
    )
from pydantic import BaseModel, Field, validator

from .constants import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
)
from .errors import ConfigError

T = TypeVar("T", bound=BaseModel)

# Default configuration file name
DEFAULT_CONFIG_FILE = "mate.yaml"


class ClientOptions(BaseModel):
    """Configuration options for the Wyse Mate client."""

    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication",
        min_length=1,
    )
    base_url: str = Field(
        default=DEFAULT_BASE_URL,
        description="Base URL for the API",
        min_length=1,
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        description="Request timeout in seconds",
        ge=1,
        le=300,
    )
    user_agent: str = Field(
        default=DEFAULT_USER_AGENT,
        description="User agent string",
        min_length=1,
    )
    debug: bool = Field(
        default=False,
        description="Enable debug logging",
    )
    http_client: Optional[Any] = Field(
        default=None,
        description="Custom HTTP client instance",
        exclude=True,
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"
        validate_assignment = True

    @validator("base_url")
    def validate_base_url(cls, v):
        """Validate base URL format."""
        if v is not None:
            if not v.startswith(("http://", "https://")):
                raise ValueError("Base URL must start with http:// or https://")
            if v.endswith("/"):
                v = v.rstrip("/")
        return v

    @validator("api_key")
    def validate_api_key(cls, v):
        """Validate API key format."""
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("API key cannot be empty")
        return v


def load_config(config_path: Type[Path]) -> ClientOptions:
    """
    Load client configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        ClientOptions: Loaded configuration options

    Raises:
        ConfigError: If configuration file cannot be loaded or parsed
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    if not config_path.is_file():
        raise ConfigError(f"Configuration path is not a file: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML content
        try:
            config_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in configuration file: {e}", cause=e)

        # Validate configuration data
        if not isinstance(config_data, dict):
            raise ConfigError("Configuration file must contain a YAML dictionary")

        return ClientOptions(**config_data)

    except IOError as e:
        raise ConfigError(f"Unable to read configuration file: {e}", cause=e)
    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(f"Unexpected error loading configuration: {e}", cause=e)


def create_default_config() -> ClientOptions:
    """
    Create a default client configuration.

    Returns:
        ClientOptions: Default configuration options
    """
    return ClientOptions(
        base_url=DEFAULT_BASE_URL,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
        debug=False,
    )


def get_default_config_path() -> Path:
    """
    Get the default configuration file path.

    Returns:
        Path: Path to the default configuration file (mate.yaml)
    """
    return Path.cwd() / DEFAULT_CONFIG_FILE


def load_default_config() -> Optional[ClientOptions]:
    """
    Load configuration from the default configuration file (mate.yaml).

    Returns:
        ClientOptions: Loaded configuration options, or None if file doesn't exist

    Raises:
        ConfigError: If configuration file exists but cannot be loaded or parsed
    """
    default_path = get_default_config_path()

    if not default_path.exists():
        return None

    return load_config(default_path)
