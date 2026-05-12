from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal, Optional

Environment = Literal["local", "remote"]
Capability = Literal["extension", "api"]
TaskType = Literal["reply", "publish", "interact"]
Expected = Literal["success", "failure"]


@dataclass(frozen=True)
class Scenario:
    id: str
    environment: Environment
    capability: Capability
    task_type: TaskType
    expected: Expected
    expected_reason: Optional[str] = None


SCENARIOS = [
    Scenario("local-extension-reply", "local", "extension", "reply", "success"),
    Scenario("local-extension-publish", "local", "extension", "publish", "success"),
    Scenario("local-extension-interact", "local", "extension", "interact", "success"),
    Scenario("local-api-reply", "local", "api", "reply", "failure", "REPLY_API_UNSUPPORTED"),
    Scenario("local-api-publish", "local", "api", "publish", "success"),
    Scenario("local-api-interact", "local", "api", "interact", "success"),
    Scenario("remote-extension-reply", "remote", "extension", "reply", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-extension-publish", "remote", "extension", "publish", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-extension-interact", "remote", "extension", "interact", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-api-reply", "remote", "api", "reply", "failure", "REPLY_API_UNSUPPORTED"),
    Scenario("remote-api-publish", "remote", "api", "publish", "success"),
    Scenario("remote-api-interact", "remote", "api", "interact", "success"),
]


def execution_mode_for(capability: Capability) -> str:
    return "api_only" if capability == "api" else "extension_only"


def browser_available_for(environment: Environment) -> bool:
    return environment == "local"


def make_run_id(run_prefix: str, scenario: Scenario) -> str:
    return f"{run_prefix}-{scenario.id}"


def make_nonce() -> str:
    return secrets.token_hex(3)


def default_run_prefix() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def filter_scenarios(
    scenario_id: Optional[str],
    environment: Optional[str],
    capability: Optional[str],
    task_type: Optional[str],
) -> list[Scenario]:
    selected: Iterable[Scenario] = SCENARIOS
    if scenario_id:
        selected = [s for s in selected if s.id == scenario_id]
    if environment:
        selected = [s for s in selected if s.environment == environment]
    if capability:
        selected = [s for s in selected if s.capability == capability]
    if task_type:
        selected = [s for s in selected if s.task_type == task_type]
    return list(selected)


def build_task_prompt(
    scenario: Scenario,
    run_id: str,
    nonce: str,
    publish_text_prefix: str,
    target_tweet_url: Optional[str],
) -> str:
    marker = f"{run_id} {nonce}"
    header = (
        f"Run ID: {run_id}\n"
        f"Nonce: {nonce}\n\n"
        "Do not ask for additional confirmation unless the system requires authorization.\n"
    )
    if scenario.task_type == "reply":
        if not target_tweet_url:
            raise ValueError("MATE_E2E_TARGET_TWEET_URL is required for reply scenarios")
        return (
            f"{header}\n"
            f"Use the configured X account to reply to this tweet: {target_tweet_url}\n"
            f"The reply must include this exact run id and nonce: {marker}."
        )
    if scenario.task_type == "publish":
        return (
            f"{header}\n"
            "Use the configured X account to publish one short test tweet.\n"
            f"The tweet text must include: {publish_text_prefix} {marker}."
        )
    if not target_tweet_url:
        raise ValueError("MATE_E2E_TARGET_TWEET_URL is required for interact scenarios")
    return (
        f"{header}\n"
        f"Use the configured X account to interact with this tweet: {target_tweet_url}\n"
        "Perform one available interaction such as like or retweet."
    )
