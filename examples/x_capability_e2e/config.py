from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from octoevo.mate import Client
from octoevo.mate.config import load_config


DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_USER_INPUT_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class E2EConfig:
    client: Client
    product_id: Optional[str]
    target_tweet_url: Optional[str]
    target_x_user: Optional[str]
    publish_text_prefix: str
    timeout_seconds: int
    user_input_timeout_seconds: int
    result_dir: Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value


def load_e2e_config(base_dir: Path) -> E2EConfig:
    config_path = base_dir / "mate.yaml"
    client = Client(load_config(str(config_path)))
    return E2EConfig(
        client=client,
        product_id=os.getenv("MATE_E2E_PRODUCT_ID", "").strip() or None,
        target_tweet_url=os.getenv("MATE_E2E_TARGET_TWEET_URL", "").strip() or None,
        target_x_user=os.getenv("MATE_E2E_TARGET_X_USER", "").strip() or None,
        publish_text_prefix=os.getenv("MATE_E2E_PUBLISH_TEXT_PREFIX", "Wyse E2E test").strip()
        or "Wyse E2E test",
        timeout_seconds=_env_int("MATE_E2E_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        user_input_timeout_seconds=_env_int(
            "MATE_E2E_USER_INPUT_TIMEOUT_SECONDS",
            DEFAULT_USER_INPUT_TIMEOUT_SECONDS,
        ),
        result_dir=base_dir / "results",
    )
