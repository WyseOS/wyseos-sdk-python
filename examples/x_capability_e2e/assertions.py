from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from octoevo.mate.task_runner import TaskResult

from scenarios import Scenario  # type: ignore

Status = Literal["PASS", "FAIL", "ERROR", "TIMEOUT"]

EXPECTED_FAILURE_CODES = {
    "REPLY_API_UNSUPPORTED",
    "EXTENSION_REQUIRED",
}
ENVIRONMENT_ERROR_CODES = {
    "ACCOUNT_IDENTIFIER_REQUIRED",
}
ENVIRONMENT_ERROR_MARKERS = {
    "noop: No pending ",
}
AUTH_ERROR_MARKERS = {
    "authorization_required",
    "oauth2 authorization is required",
    "x_api_authorize",
    "AUTH_REQUIRED",
    "TOKEN_EXPIRED",
    "INSUFFICIENT_SCOPE",
}
PLATFORM_ERROR_MARKERS = {
    "rate limit",
    "duplicate",
    "spam",
    "policy",
}
EXECUTION_FAILURE_MARKERS = {
    "partial_failed:",
    "skipped_terminal:",
    "closed without success",
    "rows still pending",
    "x api is unavailable and cannot be fixed by authorization",
}
SUCCESS_NOOP_MARKERS = {
    "reply": "check_and_reply_tweets=noop",
    "publish": "batch_post_short_tweets=noop",
    "interact": "like_and_retweet=noop",
}


@dataclass(frozen=True)
class AssertionResult:
    status: Status
    matched_reason: Optional[str] = None
    message: str = ""


def _text_parts(result: TaskResult) -> list[str]:
    parts = [result.final_answer or "", result.error or ""]
    for log in result.execution_logs:
        parts.append(str(log))
        metadata = getattr(log, "metadata", None)
        if isinstance(log, dict):
            metadata = log.get("metadata", metadata)
        if isinstance(metadata, dict):
            parts.extend(str(value) for value in metadata.values())
    return [part for part in parts if part]


def _contains(text_parts: list[str], needle: str) -> bool:
    lowered = needle.lower()
    return any(lowered in part.lower() for part in text_parts)


def classify_result(scenario: Scenario, result: TaskResult) -> AssertionResult:
    parts = _text_parts(result)
    success_marker = False
    if scenario.task_type == "publish":
        success_marker = _contains(parts, "batch_post_short_tweets=completed")
    elif scenario.task_type == "interact":
        success_marker = _contains(parts, "like_and_retweet=completed")
    elif scenario.task_type == "reply":
        success_marker = _contains(parts, "check_and_reply_tweets=completed")

    if result.error and "timeout" in result.error.lower():
        return AssertionResult("TIMEOUT", message=result.error)

    if scenario.expected == "failure":
        if scenario.expected_reason and _contains(parts, scenario.expected_reason):
            return AssertionResult("PASS", scenario.expected_reason)

    if any(_contains(parts, marker) for marker in PLATFORM_ERROR_MARKERS):
        return AssertionResult("ERROR", "platform_rejected", "Platform rejected the action")

    if any(_contains(parts, marker) for marker in EXECUTION_FAILURE_MARKERS):
        return AssertionResult(
            "FAIL",
            "execution_failed",
            "Execution reached a terminal failure state",
        )

    if any(_contains(parts, code) for code in ENVIRONMENT_ERROR_CODES):
        return AssertionResult(
            "ERROR",
            "ACCOUNT_IDENTIFIER_REQUIRED",
            "Missing X account identity",
        )

    if any(_contains(parts, marker) for marker in ENVIRONMENT_ERROR_MARKERS):
        return AssertionResult(
            "ERROR",
            "missing_pending_records",
            "No pending marketing records were prepared for the session",
        )

    if scenario.expected == "failure":
        return AssertionResult(
            "FAIL",
            scenario.expected_reason,
            "Expected failure reason was not observed",
        )

    for code in EXPECTED_FAILURE_CODES:
        if _contains(parts, code):
            return AssertionResult("FAIL", code, "Unexpected capability rejection was observed")

    noop_marker = SUCCESS_NOOP_MARKERS.get(scenario.task_type)
    if scenario.expected == "success" and noop_marker and _contains(parts, noop_marker):
        return AssertionResult(
            "FAIL",
            "noop_execution",
            "Execution completed without performing the requested action",
        )

    if success_marker and result.success and not result.error:
        return AssertionResult("PASS")

    if any(_contains(parts, marker) for marker in AUTH_ERROR_MARKERS):
        return AssertionResult(
            "FAIL",
            "authorization_required",
            "Authorization is required",
        )

    if result.success and not result.error:
        return AssertionResult("PASS")

    return AssertionResult("FAIL", message=result.error or "Task did not succeed")
