from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from octoevo.mate.task_runner import TaskResult

from scenarios import Scenario

Status = Literal["PASS", "FAIL", "ERROR", "TIMEOUT"]

FAILURE_REASON_MARKERS = {
    "api_reply_unsupported": ["api", "reply", "not support"],
    "extension_dm_unsupported": ["extension", "direct message", "not support"],
    "extension_unavailable": ["browser", "extension", "unavailable"],
}
PLATFORM_ERROR_MARKERS = ["rate limit", "duplicate", "spam", "policy"]
AUTH_ERROR_MARKERS = ["x_api_authorize", "authorization", "connector"]


@dataclass(frozen=True)
class AssertionResult:
    status: Status
    matched_reason: Optional[str] = None
    message: str = ""


def _combined_text(result: TaskResult) -> str:
    parts = [result.final_answer, result.error or ""]
    parts.extend(str(log) for log in result.execution_logs)
    return "\n".join(parts).lower()


def _contains_all(text: str, markers: list[str]) -> bool:
    return all(marker in text for marker in markers)


def classify_result(scenario: Scenario, result: TaskResult) -> AssertionResult:
    text = _combined_text(result)

    if result.error and "timeout" in result.error.lower():
        return AssertionResult("TIMEOUT", message=result.error)

    if any(marker in text for marker in PLATFORM_ERROR_MARKERS):
        return AssertionResult("ERROR", "platform_rejected", "Platform rejected the action")

    if any(marker in text for marker in AUTH_ERROR_MARKERS):
        return AssertionResult(
            "ERROR",
            "authorization_required",
            "Authorization or connector setup is required",
        )

    if scenario.expected == "failure":
        reason = scenario.expected_reason
        markers = FAILURE_REASON_MARKERS.get(reason or "")
        if reason and markers and _contains_all(text, markers):
            return AssertionResult("PASS", reason)
        return AssertionResult("FAIL", reason, "Expected failure reason was not observed")

    if not result.success:
        for reason, markers in FAILURE_REASON_MARKERS.items():
            if _contains_all(text, markers):
                return AssertionResult("FAIL", reason, "Unexpected rejection marker observed")

    if result.success and not result.error:
        return AssertionResult("PASS")

    return AssertionResult("FAIL", message=result.error or "Task did not succeed")
