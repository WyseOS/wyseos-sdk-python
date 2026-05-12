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
AUTH_ERROR_MARKERS = {
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

    if result.error and "timeout" in result.error.lower():
        return AssertionResult("TIMEOUT", message=result.error)

    if any(_contains(parts, marker) for marker in PLATFORM_ERROR_MARKERS):
        return AssertionResult("ERROR", "platform_rejected", "Platform rejected the action")

    if any(_contains(parts, code) for code in ENVIRONMENT_ERROR_CODES):
        return AssertionResult(
            "ERROR",
            "ACCOUNT_IDENTIFIER_REQUIRED",
            "Missing X account identity",
        )

    if any(_contains(parts, marker) for marker in AUTH_ERROR_MARKERS):
        return AssertionResult(
            "ERROR",
            "authorization_required",
            "Authorization is required",
        )

    if scenario.expected == "failure":
        if scenario.expected_reason and _contains(parts, scenario.expected_reason):
            return AssertionResult("PASS", scenario.expected_reason)
        return AssertionResult(
            "FAIL",
            scenario.expected_reason,
            "Expected failure reason was not observed",
        )

    for code in EXPECTED_FAILURE_CODES:
        if _contains(parts, code):
            return AssertionResult("FAIL", code, "Unexpected capability rejection was observed")

    if result.success and not result.error:
        return AssertionResult("PASS")

    return AssertionResult("FAIL", message=result.error or "Task did not succeed")
