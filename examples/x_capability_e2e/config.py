from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from octoevo.mate import Client
from octoevo.mate.config import load_config


DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_USER_INPUT_TIMEOUT_SECONDS = 120
DEFAULT_PUBLISH_TEXT_PREFIX = "fictions:"


@dataclass(frozen=True)
class E2EConfig:
    client: Client
    reply_tweet_url: Optional[str]
    publish_text_prefix: str
    timeout_seconds: int
    user_input_timeout_seconds: int
    result_dir: Path


def load_e2e_config(base_dir: Path) -> E2EConfig:
    config_path = base_dir / "mate.yaml"
    client = Client(load_config(str(config_path)))
    return E2EConfig(
        client=client,
        reply_tweet_url=os.getenv("MATE_E2E_REPLY_TWEET_URL", "").strip() or None,
        publish_text_prefix=DEFAULT_PUBLISH_TEXT_PREFIX,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        user_input_timeout_seconds=DEFAULT_USER_INPUT_TIMEOUT_SECONDS,
        result_dir=base_dir / "results",
    )
