from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from assertions import AssertionResult, classify_result  # type: ignore
from config import E2EConfig  # type: ignore
from scenarios import (  # type: ignore
    Scenario,
    browser_available_for,
    build_task_prompt,
    execution_mode_for,
    make_nonce,
    make_run_id,
)

from octoevo.mate import create_task_runner
from octoevo.mate.models import CreateSessionRequest
from octoevo.mate.task_runner import TaskExecutionOptions, TaskMode, TaskResult
from octoevo.mate.websocket import WebSocketClient

DEFAULT_MARKETING_SKILLS = [
    {
        "skill_id": "7ccfb3d7-e6ac-4cda-bce3-030768ef9a9",
        "skill_name": "persona",
    }
]


@dataclass(frozen=True)
class ScenarioRunResult:
    scenario_id: str
    session_id: Optional[str]
    environment: str
    capability: str
    task_type: str
    execution_mode: str
    browser_available: bool
    expected: str
    status: str
    matched_reason: Optional[str]
    started_at: datetime
    ended_at: datetime
    duration_seconds: float

    def to_json(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "session_id": self.session_id,
            "environment": self.environment,
            "capability": self.capability,
            "task_type": self.task_type,
            "expected": self.expected,
            "status": self.status,
            "matched_reason": self.matched_reason,
            "started_at": _iso(self.started_at),
            "ended_at": _iso(self.ended_at),
            "duration_seconds": self.duration_seconds,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _append_log(log_path: Path, text: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(text.rstrip())
        f.write("\n")


def _build_extra(config: E2EConfig, execution_mode: str) -> Dict[str, Any]:
    extra: Dict[str, Any] = {
        "skills": DEFAULT_MARKETING_SKILLS,
        "execution_mode": execution_mode,
    }
    if config.product_id:
        extra["marketing_product"] = {"product_id": config.product_id}
    return extra


def _write_task_log(
    log_path: Path,
    scenario: Scenario,
    session_id: Optional[str],
    result: TaskResult,
    assertion: AssertionResult,
) -> None:
    _append_log(log_path, f"scenario_id: {scenario.id}")
    _append_log(log_path, f"session_id: {session_id or ''}")
    _append_log(log_path, f"status: {assertion.status}")
    _append_log(log_path, f"matched_reason: {assertion.matched_reason or ''}")
    _append_log(log_path, f"message: {assertion.message}")
    _append_log(log_path, f"result.error: {result.error or ''}")
    _append_log(log_path, f"result.final_answer: {result.final_answer}")
    _append_log(log_path, "execution_logs:")
    for item in result.execution_logs:
        _append_log(log_path, f"- {item}")
    _append_log(log_path, "")


def run_scenario(
    config: E2EConfig,
    scenario: Scenario,
    run_prefix: str,
    log_path: Path,
) -> ScenarioRunResult:
    started_at = _now()
    session_id: Optional[str] = None
    execution_mode = execution_mode_for(scenario.capability)
    browser_available = browser_available_for(scenario.environment)
    nonce = make_nonce()
    run_id = make_run_id(run_prefix, scenario)

    try:
        task = build_task_prompt(
            scenario=scenario,
            run_id=run_id,
            nonce=nonce,
            publish_text_prefix=config.publish_text_prefix,
            target_tweet_url=config.target_tweet_url,
        )
        extra = _build_extra(config, execution_mode)
        req = CreateSessionRequest(
            task=task,
            mode=TaskMode.Marketing.value,
            platform="api",
            extra=extra,
        )
        session = config.client.session.create(req)
        session_id = session.session_id
        session_info = config.client.session.get_info(session_id)
        ws_client = WebSocketClient(
            base_url=config.client.base_url,
            api_key=config.client.api_key or "",
            jwt_token=config.client.jwt_token or "",
            session_id=session_info.session_id,
        )
        task_runner = create_task_runner(ws_client, config.client, session_info)
        result = task_runner.run_task(
            task=task,
            task_mode=TaskMode.Marketing,
            extra=extra,
            options=TaskExecutionOptions(
                auto_accept_plan=True,
                verbose=False,
                completion_timeout=config.timeout_seconds,
                max_user_input_timeout=config.user_input_timeout_seconds,
                browser_available=browser_available,
                enable_event_logging=True,
            ),
        )
        assertion = classify_result(scenario, result)
        _write_task_log(log_path, scenario, session_id, result, assertion)
    except Exception:
        error = traceback.format_exc()
        assertion = AssertionResult("ERROR", message=error)
        result = TaskResult(success=False, error=error)
        _write_task_log(log_path, scenario, session_id, result, assertion)

    ended_at = _now()
    return ScenarioRunResult(
        scenario_id=scenario.id,
        session_id=session_id,
        environment=scenario.environment,
        capability=scenario.capability,
        task_type=scenario.task_type,
        execution_mode=execution_mode,
        browser_available=browser_available,
        expected=scenario.expected,
        status=assertion.status,
        matched_reason=assertion.matched_reason,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=(ended_at - started_at).total_seconds(),
    )
