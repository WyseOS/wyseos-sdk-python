from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from octoevo.mate import Client
from octoevo.mate.config import load_config

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_USER_INPUT_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class E2EConfig:
    client: Client
    product_id: Optional[str]
    product_name: Optional[str]
    target_tweet_url: Optional[str]
    publish_text_prefix: str
    timeout_seconds: int
    user_input_timeout_seconds: int
    result_dir: Path


def load_e2e_config(base_dir: Path) -> E2EConfig:
    config_path = base_dir / "mate.yaml"
    client = Client(load_config(str(config_path)))
    product_id = os.getenv("MATE_E2E_PRODUCT_ID", "").strip() or None
    product_name = os.getenv("MATE_E2E_PRODUCT_NAME", "").strip() or None
    if product_id and not product_name:
        try:
            info = client.product.get_info(product_id)
        except Exception as exc:
            logger.warning("Failed to resolve product name for %s: %s", product_id, exc)
        else:
            product_name = info.product_name.strip() or None
    return E2EConfig(
        client=client,
        product_id=product_id,
        product_name=product_name,
        target_tweet_url=os.getenv("MATE_E2E_TARGET_TWEET_URL", "").strip() or None,
        publish_text_prefix=os.getenv("MATE_E2E_PUBLISH_TEXT_PREFIX", "Wyse E2E test").strip()
        or "Wyse E2E test",
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        user_input_timeout_seconds=DEFAULT_USER_INPUT_TIMEOUT_SECONDS,
        result_dir=base_dir / "results",
    )
