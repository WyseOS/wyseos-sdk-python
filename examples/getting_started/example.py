#!/usr/bin/env python3
"""
Minimal marketing example for WyseOS Python SDK.
"""

import logging
import os
from typing import Dict, List

from wyseos.mate import Client, ClientOptions, create_task_runner
from wyseos.mate.config import load_config
from wyseos.mate.models import CreateSessionRequest
from wyseos.mate.task_runner import TaskExecutionOptions, TaskMode
from wyseos.mate.websocket import WebSocketClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Keep JS-aligned default skills for reusable marketing demo.
DEFAULT_MARKETING_SKILLS: List[Dict[str, str]] = [
    {
        "skill_id": "7ccfb3d7-e6ac-4cda-bce3-030768ef9a9",
        "skill_name": "persona",
    }
]
CLI_SAFE_EXTRA_INSTRUCTION = (
    "只生成内容，不执行发布/点赞/转推等浏览器操作。"
)


def create_client() -> Client | None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mate.yaml")
    try:
        print(f"Loading config from {config_path}")
        return Client(load_config(config_path))
    except Exception as e:
        print(f"Failed to load config: {e}")
        print("Please configure mate.yaml with a valid api_key or jwt_token.")
        return None


def build_extra(product_id: str) -> Dict:
    extra = {"skills": DEFAULT_MARKETING_SKILLS}
    if product_id:
        extra["marketing_product"] = {"product_id": product_id}
    return extra


def main():
    client = create_client()
    if not client:
        return

    task = input("Enter TASK: ").strip()
    if not task:
        print("TASK is required")
        return
    task = f"{task}\n\n额外要求：{CLI_SAFE_EXTRA_INSTRUCTION}"

    product_id = input("Enter PRODUCT_ID (optional): ").strip()
    extra = build_extra(product_id)

    req = CreateSessionRequest(
        task=task,
        mode=TaskMode.Marketing.value,
        platform="api",
        extra=extra,
    )
    session = client.session.create(req)
    session_info = client.session.get_info(session.session_id)
    print(f"Created marketing session: {session.session_id}")

    ws_client = WebSocketClient(
        base_url=client.base_url,
        api_key=client.api_key or "",
        jwt_token=client.jwt_token or "",
        session_id=session_info.session_id,
        heartbeat_interval=30,
    )
    task_runner = create_task_runner(ws_client, client, session_info)

    options = TaskExecutionOptions(
        auto_accept_plan=False,
        verbose=True,
        stop_on_x_confirm=True,
        completion_timeout=600,
    )

    print("Starting interactive marketing session...")
    task_runner.run_interactive_session(
        initial_task=task,
        task_mode=TaskMode.Marketing,
        extra=extra,
        options=options,
    )


if __name__ == "__main__":
    main()
