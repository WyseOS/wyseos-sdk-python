from __future__ import annotations

import random
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional

from assertions import AssertionResult, classify_result  # type: ignore
from config import E2EConfig  # type: ignore
from scenarios import (  # type: ignore
    Scenario,
    browser_available_for,
    build_execute_task_prompt,
    build_reply_browser_seed_task_prompt,
    build_seed_task_prompt,
    execution_mode_for,
    marketing_data_counts_for,
    make_nonce,
    make_run_id,
)

from octoevo.mate.models import CreateSessionRequest
from octoevo.mate.task_runner import (
    ExecutionMode,
    TaskExecutionOptions,
    TaskMode,
    TaskResult,
    TaskRunner,
)
from octoevo.mate.websocket import WebSocketClient

DEFAULT_MARKETING_SKILLS = [
    {
        "skill_id": "7ccfb3d7-e6ac-4cda-bce3-030768ef9a9f",
        "skill_name": "persona",
    }
]
SEED_TIMEOUT_FLOOR_SECONDS = 180
MARKETING_BATCH_COMPLETED_PREFIX = "Marketing batch completed:"
DEFAULT_MARKETING_PRODUCT_NAME = "Hyperagent"
DEFAULT_MARKETING_PRODUCT_ID = "5aa3c256-6954-424f-833a-9d3bfaf96a4b"


def should_stop_on_marketing_batch(content: str, stream_label: str) -> bool:
    if not content.startswith(MARKETING_BATCH_COMPLETED_PREFIX):
        return False
    return stream_label != "seed"


class E2ETaskRunner(TaskRunner):
    """Stop early on clear terminal text emitted by the agent."""

    def __init__(
        self,
        ws_client,
        client,
        session_info,
        ignored_message_ids: Optional[set[str]] = None,
        stream_label: str = "task",
    ):
        super().__init__(ws_client, client, session_info)
        self._ignored_message_ids = ignored_message_ids or set()
        self._stream_label = stream_label
        self._stream_index = 0

    @staticmethod
    def _display_content(content: Any) -> Optional[str]:
        text = str(content or "")
        if not text:
            return None
        lines = text.splitlines()
        if len(lines) >= 2 and lines[0].startswith("Run ID: ") and lines[1].startswith("Nonce: "):
            lines = lines[2:]
            while lines and not lines[0].strip():
                lines.pop(0)
            text = "\n".join(lines).strip()
        return text or None

    def _print_live_message(self, message: Dict[str, Any]) -> None:
        source = str(message.get("source") or "unknown")
        msg_type = str(message.get("type") or "unknown")
        metadata = message.get("metadata")
        content = self._display_content(message.get("content"))
        x_api_authorize_payload = self._authorization.extract_payload(message)

        self._stream_index += 1
        print(f"[{self._stream_label}][{self._stream_index}] {source} ({msg_type})")
        if isinstance(metadata, dict) and metadata:
            print(f"metadata: {json.dumps(metadata, ensure_ascii=False, default=str)}")
        if content not in (None, ""):
            print(content)
        if x_api_authorize_payload:
            auth_url = str(x_api_authorize_payload.get("auth_url") or "").strip()
            reason_message = str(x_api_authorize_payload.get("reason_message") or "").strip()
            if reason_message and reason_message != content:
                print(reason_message)
            if auth_url:
                print(f"auth_url: {auth_url}")

    def _handle_terminal_x_api_authorize(
        self,
        x_api_authorize_payload: Dict[str, Any],
        result_container: Dict,
        completion_events: Dict,
        options: TaskExecutionOptions,
        timestamp: str,
    ) -> None:
        error = self._authorization.start(x_api_authorize_payload)
        if error:
            result_container["has_error"] = True
            result_container["error"] = error
            completion_events["error"].set()
            return

        self._handle_x_api_authorize_message(
            self._authorization.state,
            options,
            timestamp,
        )
        request_id = self._authorization.state.request_id
        if not request_id:
            return
        if not sys.stdin.isatty():
            result_container["has_error"] = True
            result_container["error"] = (
                "authorization_required: terminal input is unavailable; "
                "complete X authorization in an interactive terminal."
            )
            completion_events["error"].set()
            return

        try:
            user_input = input("Complete authorization, then press Enter to continue: ").strip()
        except EOFError:
            user_input = ""

        self.ws_client.send_message(
            WebSocketClient.create_text_input_response(
                request_id,
                self._authorization.build_resume_text(user_input),
            )
        )
        self._clear_pending_input_state()
        print("-> Sent authorization response")

    def _handle_x_api_account_select(
        self,
        payload: Dict[str, Any],
        result_container: Dict,
        completion_events: Dict,
    ) -> None:
        error = self._account_selection.start(payload)
        if error:
            result_container["has_error"] = True
            result_container["error"] = error
            completion_events["error"].set()
            return

        request_id = self._account_selection.state.request_id
        if not request_id:
            return
        selected = random.choice(self._account_selection.state.accounts)
        response_text = self._account_selection.build_selection_response_text(selected)
        self.ws_client.send_message(
            WebSocketClient.create_text_input_response(request_id, response_text)
        )
        self._clear_pending_input_state()
        username = str(
            selected.get("external_username") or selected.get("external_user_id") or ""
        ).strip()
        print(f"-> Auto-selected X account: {username or 'unknown'}")

    def _handle_message(
        self,
        message: Dict[str, Any],
        result_container: Dict,
        completion_events: Dict,
        options: TaskExecutionOptions,
    ):
        message_id = str(message.get("message_id") or "")
        if message_id and message_id in self._ignored_message_ids:
            return
        self._print_live_message(message)
        x_api_authorize_payload = self._authorization.extract_payload(message)
        if x_api_authorize_payload is not None:
            timestamp = datetime.now(timezone.utc).isoformat()
            self._handle_terminal_x_api_authorize(
                x_api_authorize_payload,
                result_container,
                completion_events,
                options,
                timestamp,
            )
            return
        x_api_account_select_payload = self._account_selection.extract_payload(message)
        if x_api_account_select_payload is not None:
            self._handle_x_api_account_select(
                x_api_account_select_payload,
                result_container,
                completion_events,
            )
            return
        super()._handle_message(message, result_container, completion_events, options)
        if completion_events["task_completed"].is_set() or completion_events["error"].is_set():
            return

        content = str(message.get("content") or "")
        if not content:
            return

        if "Extension session disconnected." in content:
            result_container["has_error"] = True
            result_container["error"] = f"EXTENSION_REQUIRED: {content}"
            completion_events["error"].set()
            return

        if content.startswith("noop: No pending "):
            result_container["has_error"] = True
            result_container["error"] = content
            completion_events["error"].set()
            return

        if content.startswith("partial_failed: Target X account identity is required"):
            result_container["has_error"] = True
            result_container["error"] = f"ACCOUNT_IDENTIFIER_REQUIRED: {content}"
            completion_events["error"].set()
            return

        if content.startswith("partial_failed: Reply is extension-only; api_only cannot run reply tasks."):
            result_container["has_error"] = True
            result_container["error"] = f"REPLY_API_UNSUPPORTED: {content}"
            completion_events["error"].set()
            return

        if should_stop_on_marketing_batch(content, self._stream_label):
            result_container["final_answer"] = content
            result_container["task_completed"] = True
            result_container["task_completed_at"] = time.time()
            completion_events["task_completed"].set()


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


def _build_extra() -> Dict[str, Any]:
    return {
        "skills": DEFAULT_MARKETING_SKILLS,
        "marketing_product": {"product_id": DEFAULT_MARKETING_PRODUCT_ID},
    }


def _product_context() -> str:
    return f"Product context: {DEFAULT_MARKETING_PRODUCT_NAME}."


def _with_product_context(scenario: Scenario, task: str) -> str:
    if scenario.task_type != "interact":
        return task
    return f"{task}\n\n{_product_context()}"


def _seed_data_types_for(scenario: Scenario) -> tuple[str, ...]:
    if scenario.task_type == "reply":
        return ("reply",)
    if scenario.task_type == "publish":
        return ("tweet",)
    return ("like", "retweet")


def _fetch_marketing_data(config: E2EConfig, session_id: str, scenario: Scenario) -> dict[str, dict]:
    data: dict[str, dict] = {}
    for data_type in _seed_data_types_for(scenario):
        data[data_type] = config.client.session.get_marketing_data(session_id, type=data_type)
    return data


def _has_seeded_marketing_data(data_counts: dict[str, int]) -> bool:
    return any(count > 0 for count in data_counts.values())


def _seed_completed_without_marketing_data(scenario: Scenario, seed_result: TaskResult) -> bool:
    if scenario.task_type != "reply":
        return False
    parts = [seed_result.final_answer or "", seed_result.error or ""]
    for log in seed_result.execution_logs:
        parts.append(str(log))
    markers = (
        "reply draft about yc-bench has been successfully created and saved",
        "saved as the current session reply draft",
        "Here is the single reply draft about yc-bench",
    )
    lowered_parts = [part.lower() for part in parts if part]
    return any(marker.lower() in part for marker in markers for part in lowered_parts)


def _should_retry_reply_seed_with_browser(scenario: Scenario, seed_result: TaskResult) -> bool:
    if scenario.task_type != "reply":
        return False
    parts = [seed_result.final_answer or "", seed_result.error or ""]
    for log in seed_result.execution_logs:
        parts.append(str(log))
    lowered_parts = [part.lower() for part in parts if part]
    retry_markers = (
        "no tweets found to reply to",
        "check_and_reply_tweets=noop",
    )
    return any(marker in part for marker in retry_markers for part in lowered_parts)


def _run_session_task(
    config: E2EConfig,
    session_id: str,
    task: str,
    extra: Dict[str, Any],
    execution_mode: Optional[str],
    browser_available: bool,
    timeout_seconds: Optional[int] = None,
    ignored_message_ids: Optional[set[str]] = None,
    stream_label: str = "task",
) -> TaskResult:
    session_info = config.client.session.get_info(session_id)
    ws_client = WebSocketClient(
        base_url=config.client.base_url,
        api_key=config.client.api_key or "",
        jwt_token=config.client.jwt_token or "",
        session_id=session_info.session_id,
    )
    task_runner = E2ETaskRunner(
        ws_client,
        config.client,
        session_info,
        ignored_message_ids=ignored_message_ids,
        stream_label=stream_label,
    )
    return task_runner.run_task(
        task=task,
        task_mode=TaskMode.Marketing,
        extra=extra,
        execution_mode=ExecutionMode(execution_mode) if execution_mode else None,
        options=TaskExecutionOptions(
            auto_accept_plan=True,
            verbose=True,
            completion_timeout=timeout_seconds or config.timeout_seconds,
            max_user_input_timeout=config.user_input_timeout_seconds,
            browser_available=browser_available,
            enable_event_logging=True,
        ),
    )


def _session_message_ids(config: E2EConfig, session_id: str) -> set[str]:
    ids: set[str] = set()
    messages = config.client.session.get_messages(session_id, page_num=1, page_size=200)
    for message in messages.messages:
        message_id = str(getattr(message, "message_id", "") or "")
        if message_id:
            ids.add(message_id)
    return ids


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
        seed_task = build_seed_task_prompt(
            scenario=scenario,
            run_id=run_id,
            nonce=nonce,
            publish_text_prefix=config.publish_text_prefix,
            reply_tweet_url=config.reply_tweet_url,
        )
        seed_task = _with_product_context(scenario, seed_task)
        seed_extra = _build_extra()
        req = CreateSessionRequest(
            task=seed_task,
            mode=TaskMode.Marketing.value,
            platform="api",
            extra=seed_extra,
        )
        session = config.client.session.create(req)
        session_id = session.session_id
        print(f"[session] {session_id}")
        seed_result = _run_session_task(
            config=config,
            session_id=session_id,
            task=seed_task,
            extra=seed_extra,
            execution_mode=None,
            browser_available=browser_available,
            timeout_seconds=max(config.timeout_seconds, SEED_TIMEOUT_FLOOR_SECONDS),
            stream_label="seed",
        )
        data_by_type = _fetch_marketing_data(config, session_id, scenario)
        data_counts = marketing_data_counts_for(scenario, data_by_type)
        if (
            not _has_seeded_marketing_data(data_counts)
            and browser_available
            and config.reply_tweet_url
            and _should_retry_reply_seed_with_browser(scenario, seed_result)
        ):
            browser_seed_task = build_reply_browser_seed_task_prompt(
                run_id=run_id,
                nonce=nonce,
                reply_tweet_url=config.reply_tweet_url,
            )
            print("[seed] retry with browser fallback")
            seed_result = _run_session_task(
                config=config,
                session_id=session_id,
                task=browser_seed_task,
                extra=seed_extra,
                execution_mode=None,
                browser_available=browser_available,
                timeout_seconds=max(config.timeout_seconds, SEED_TIMEOUT_FLOOR_SECONDS),
                ignored_message_ids=_session_message_ids(config, session_id),
                stream_label="seed",
            )
            data_by_type = _fetch_marketing_data(config, session_id, scenario)
            data_counts = marketing_data_counts_for(scenario, data_by_type)
        if not _has_seeded_marketing_data(data_counts):
            if _seed_completed_without_marketing_data(scenario, seed_result):
                data_counts = {"reply": 1}
            else:
                if seed_result.error and "timeout" in seed_result.error.lower():
                    result = TaskResult(
                        success=False,
                        error=seed_result.error,
                        execution_logs=seed_result.execution_logs,
                    )
                    assertion = AssertionResult(
                        "TIMEOUT",
                        "seed_timeout",
                        "Marketing data seed timed out before records were created",
                    )
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
                result = TaskResult(
                    success=False,
                    error=(
                        "No pending marketing records were prepared for this session. "
                        f"seed_result_error={seed_result.error or ''}"
                    ),
                    execution_logs=seed_result.execution_logs,
                )
                assertion = AssertionResult(
                    "ERROR",
                    "missing_pending_records",
                    "No pending marketing records were prepared for the session",
                )
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

        execute_task = build_execute_task_prompt(
            scenario=scenario,
            run_id=run_id,
            nonce=nonce,
            publish_text_prefix=config.publish_text_prefix,
        )
        execute_extra = _build_extra()
        ignored_message_ids = _session_message_ids(config, session_id)
        result = _run_session_task(
            config=config,
            session_id=session_id,
            task=execute_task,
            extra=execute_extra,
            execution_mode=execution_mode,
            browser_available=browser_available,
            ignored_message_ids=ignored_message_ids,
            stream_label="execute",
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
