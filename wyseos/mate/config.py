"""
Configuration management for the WyseOS Python SDK.
"""

from pathlib import Path
from typing import Optional, TypeVar, Union

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
    DEFAULT_CONFIG_FILE,
    DEFAULT_TIMEOUT,
)
from .errors import ConfigError

T = TypeVar("T", bound=BaseModel)


class ClientOptions(BaseModel):
    """Configuration options for the WyseOS client."""

    api_key: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    base_url: str = Field(
        default=DEFAULT_BASE_URL,
        min_length=1,
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        ge=1,
        le=300,
    )

    class Config:
        extra = "forbid"
        validate_assignment = True

    @validator("base_url")
    def validate_base_url(cls, v):
        if v is not None:
            if not v.startswith(("http://", "https://")):
                raise ValueError("Base URL must start with http:// or https://")
            if v.endswith("/"):
                v = v.rstrip("/")
        return v

    @validator("api_key")
    def validate_api_key(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("API key cannot be empty")
        return v


def load_config(config_path: Optional[Union[str, Path]] = None) -> ClientOptions:
    if config_path is None:
        config_path = Path.cwd() / DEFAULT_CONFIG_FILE
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    if not config_path.is_file():
        raise ConfigError(f"Configuration path is not a file: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            config_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in configuration file: {e}", cause=e)

        if not isinstance(config_data, dict):
            raise ConfigError("Configuration file must contain a YAML dictionary")

        # If a 'mate' key exists at the top level, use that as the config dict
        if "mate" in config_data and isinstance(config_data["mate"], dict):
            config_data = config_data["mate"]

        return ClientOptions(**config_data)

    except IOError as e:
        raise ConfigError(f"Unable to read configuration file: {e}", cause=e)
    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(f"Unexpected error loading configuration: {e}", cause=e)
