"""
Extension host resolution helpers.
"""

import importlib
import os
from typing import Optional

EXTENSION_WEBAPP_HOST_ENV = "MATE_EXTENSION_WEBAPP_HOST"
DEFAULT_EXTENSION_WEBAPP_HOST = "https://weclaw.ai"


def resolve_build_extension_host() -> Optional[str]:
    try:
        build_module = importlib.import_module("._build_extension_host", package=__package__)
        build_host = getattr(build_module, "DEFAULT_EXTENSION_WEBAPP_HOST", "")
        if isinstance(build_host, str) and build_host.strip():
            return build_host.strip().rstrip("/")
    except Exception:
        return None
    return None


def resolve_extension_webapp_host() -> str:
    env_host = os.getenv(EXTENSION_WEBAPP_HOST_ENV, "").strip()
    if env_host:
        return env_host.rstrip("/")
    return resolve_build_extension_host() or DEFAULT_EXTENSION_WEBAPP_HOST
