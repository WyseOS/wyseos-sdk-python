from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal, Optional

Environment = Literal["local", "remote"]
Capability = Literal["extension", "api", "auto"]
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
    Scenario("local-auto-reply", "local", "auto", "reply", "success"),
    Scenario("local-auto-publish", "local", "auto", "publish", "success"),
    Scenario("local-auto-interact", "local", "auto", "interact", "success"),
    Scenario("remote-extension-reply", "remote", "extension", "reply", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-extension-publish", "remote", "extension", "publish", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-extension-interact", "remote", "extension", "interact", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-api-reply", "remote", "api", "reply", "failure", "REPLY_API_UNSUPPORTED"),
    Scenario("remote-api-publish", "remote", "api", "publish", "success"),
    Scenario("remote-api-interact", "remote", "api", "interact", "success"),
    Scenario("remote-auto-reply", "remote", "auto", "reply", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-auto-publish", "remote", "auto", "publish", "success"),
    Scenario("remote-auto-interact", "remote", "auto", "interact", "success"),
]


def execution_mode_for(capability: Capability) -> str:
    if capability == "api":
        return "api_only"
    if capability == "extension":
        return "extension_only"
    return "auto"


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
) -> str:
    return build_execute_task_prompt(
        scenario=scenario,
        run_id=run_id,
        nonce=nonce,
        publish_text_prefix=publish_text_prefix,
    )


def build_seed_task_prompt(
    scenario: Scenario,
    run_id: str,
    nonce: str,
    publish_text_prefix: str,
    reply_tweet_url: Optional[str],
) -> str:
    marker = f"{run_id} {nonce}"
    header = f"Run ID: {run_id}\nNonce: {nonce}\n\n"
    guard = (
        "\nDo not analyze the product."
        "\nDo not create a strategy, campaign, or multi-step plan."
        "\nDo not ask follow-up questions."
        "\nFinish immediately after the draft or record is saved."
    )
    if scenario.task_type == "reply":
        if not reply_tweet_url:
            raise ValueError("MATE_E2E_REPLY_TWEET_URL is required for reply scenarios")
        return (
            f"{header}\n"
            f"Write exactly one reply draft for this tweet: {reply_tweet_url}\n"
            "Save it as the current session reply draft.\n"
            "Do not publish the reply.\n"
            f"The reply draft must include this exact run id and nonce: {marker}."
            f"{guard}"
        )
    if scenario.task_type == "publish":
        return (
            f"{header}\n"
            "Write exactly one short tweet draft.\n"
            "Save it as the current session tweet draft.\n"
            "Do not publish the tweet.\n"
            f"The draft text must include: {publish_text_prefix} {marker}."
            f"{guard}"
        )
    return (
        f"{header}\n"
        "Find exactly one existing X post suitable for account nurturing.\n"
        "Use the marketing researcher find_tweets workflow, then submit exactly one result.\n"
        "Save it as pending current session marketing interaction data for the next execution step.\n"
        "Pipeline Context:\n"
        "- [待执行] nurture_account / like_tweets: consume exactly one tweet from this research result.\n"
        "Set like_count=1 and retweet_count=0.\n"
        "The researcher may search and choose a different suitable tweet.\n"
        "Do not call like_and_retweet or any other execution batch during this seed step.\n"
        "Do not execute the interaction during this seed step.\n"
        "Do not reply.\n"
        f"{guard}"
    )


def build_reply_browser_seed_task_prompt(
    run_id: str,
    nonce: str,
    reply_tweet_url: str,
) -> str:
    marker = f"{run_id} {nonce}"
    header = f"Run ID: {run_id}\nNonce: {nonce}\n\n"
    return (
        f"{header}\n"
        f"Open this exact tweet in the browser: {reply_tweet_url}\n"
        "Write exactly one reply draft using the tweet that is visible on the page.\n"
        "Save it as the current session reply draft.\n"
        "Do not publish the reply.\n"
        "Do not use marketing batch tools.\n"
        f"The reply draft must include this exact run id and nonce: {marker}.\n"
        "Do not analyze the product.\n"
        "Do not create a strategy, campaign, or multi-step plan.\n"
        "Do not ask follow-up questions.\n"
        "Finish immediately after the draft or record is saved."
    )


def build_execute_task_prompt(
    scenario: Scenario,
    run_id: str,
    nonce: str,
    publish_text_prefix: str,
) -> str:
    marker = f"{run_id} {nonce}"
    header = f"Run ID: {run_id}\nNonce: {nonce}\n\n"
    if scenario.task_type == "reply":
        return (
            f"{header}\n"
            "Publish the existing reply draft already saved in this session.\n"
            "Do not write a new reply.\n"
            "Do not ask for additional confirmation unless the system requires authorization.\n"
            f"Use the reply draft that includes: {marker}."
        )
    if scenario.task_type == "publish":
        return (
            f"{header}\n"
            "Publish the existing tweet draft already saved in this session.\n"
            "Do not write a new tweet.\n"
            "Do not ask for additional confirmation unless the system requires authorization.\n"
            f"Use the tweet draft that includes: {publish_text_prefix} {marker}."
        )
    return (
        f"{header}\n"
        "Run the nurture_account / like_and_retweet execution step for the current session.\n"
        "Consume exactly one existing pending tweet_interact record.\n"
        "Do not search for new tweets.\n"
        "Do not create new interaction candidates.\n"
        "Do not reply.\n"
        "Do not ask for additional confirmation unless the system requires authorization.\n"
        "Execute the prepared like interaction only."
    )


def marketing_data_counts_for(scenario: Scenario, data_by_type: dict[str, dict]) -> dict[str, int]:
    if scenario.task_type == "reply":
        return {"reply": len(data_by_type["reply"].get("reply", []))}
    if scenario.task_type == "publish":
        return {"tweet": len(data_by_type["tweet"].get("tweet", []))}
    return {
        "like": len(data_by_type["like"].get("like", [])),
        "retweet": len(data_by_type["retweet"].get("retweet", [])),
    }
