"""
Task runner: high-level task execution interface.
"""

import datetime
import json
import logging
import threading
import time
import webbrowser
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from pydantic import BaseModel

from .constants import (
    RICH_TYPE_FOLLOW_UP_SUGGESTION,
    RICH_TYPE_MARKETING_REPORT,
    RICH_TYPE_MARKETING_RESEARCH_TWEETS,
    RICH_TYPE_MARKETING_TWEET_INTERACT,
    RICH_TYPE_MARKETING_TWEET_REPLY,
    RICH_TYPE_WRITER_TWITTER,
)
from .errors import SessionExecutionError
from .plan import Plan
from .websocket import EventLog, InputType, MessageType, PlanType, WebSocketClient

logger = logging.getLogger(__name__)


def _open_url(url: str) -> None:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url, new=2)


FOLLOW_UP_GRACE_SECONDS = 1.5
CONNECT_WAIT_TIMEOUT_SECONDS = 10.0
CONNECT_POLL_INTERVAL_SECONDS = 0.05
INTERACTIVE_IDLE_DEBUG_INTERVAL_SECONDS = 10.0


class TaskExecutionOptions(BaseModel):
    """Configuration options for task execution."""

    # SDK default is quiet; examples can explicitly turn it on.
    verbose: bool = False
    auto_accept_plan: bool = True
    capture_screenshots: bool = (
        False  # Default off to avoid unnecessary resource consumption
    )
    enable_browser_logging: bool = True
    # Backward-compatible alias for old option name.
    enable_event_logging: Optional[bool] = None
    completion_timeout: int = 300  # 5 minutes
    max_user_input_timeout: int = 0  # User input timeout, 0 means infinite wait
    stop_on_x_confirm: bool = False  # For CLI safe mode: stop instead of confirming action

    @property
    def event_logging_enabled(self) -> bool:
        if self.enable_event_logging is not None:
            return self.enable_event_logging
        return self.verbose


class TaskResult(BaseModel):
    """Task execution result."""

    success: bool
    final_answer: str = ""
    error: Optional[str] = None
    screenshots: List[
        Dict[str, Any]
    ] = []  # Only contains data when capture_screenshots=True
    execution_logs: List[Dict[str, Any]] = []  # Detailed execution event logs
    plan_history: List[Dict[str, Any]] = []  # Plan change history
    session_duration: float = 0.0  # Session duration in seconds
    message_count: int = 0  # Total number of messages processed


class TaskMode(Enum):
    """Task execution mode, empty means default mode."""

    Default = ""
    DeepSearch = "deep_search"
    Marketing = "marketing"


class TaskRunner:
    """High-level task execution interface."""

    def __init__(self, ws_client: WebSocketClient, client, session_info):
        self.ws_client = ws_client
        self.client = client
        self.session_info = session_info
        self._plan_state: Optional[Plan] = None
        self._execution_logs: List[EventLog] = []
        self._raw_messages: List[Dict[str, Any]] = []
        self._start_time = 0.0
        self._pending_request_id: Optional[str] = None
        self._pending_input_type: str = InputType.TEXT
        self._pending_request_at: float = 0.0
        self._marketing_chunk_buffers: Dict[str, Any] = {}

    def _wait_until_connected(self, timeout_seconds: float = CONNECT_WAIT_TIMEOUT_SECONDS) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if self.ws_client.connected:
                return True
            if self.ws_client.thread and not self.ws_client.thread.is_alive():
                break
            time.sleep(CONNECT_POLL_INTERVAL_SECONDS)
        return self.ws_client.connected

    def _check_user_input_timeout(
        self,
        options: TaskExecutionOptions,
        result_container: Dict,
        completion_events: Dict,
    ) -> None:
        if options.max_user_input_timeout <= 0 or not self._pending_request_id:
            return
        if self._pending_request_at <= 0:
            self._pending_request_at = time.time()
            return
        elapsed = time.time() - self._pending_request_at
        if elapsed < options.max_user_input_timeout:
            return

        msg = f"User input timeout after {options.max_user_input_timeout} seconds"
        logger.warning(msg)
        result_container["has_error"] = True
        result_container["error"] = msg
        self._pending_request_id = None
        self._pending_input_type = InputType.TEXT
        self._pending_request_at = 0.0
        completion_events["error"].set()

    def run_task(
        self,
        task: str,
        attachments: List[Dict] = None,
        task_mode: TaskMode = TaskMode.Default,
        extra: Optional[Dict[str, Any]] = None,
        options: TaskExecutionOptions = None,
    ) -> TaskResult:
        """Execute a single task and return complete result."""
        if options is None:
            options = TaskExecutionOptions()

        result_container = {
            "final_answer": "",
            "task_completed": False,
            "has_error": False,
            "error": None,
            "screenshots": [],
        }

        completion_events = {
            "task_completed": threading.Event(),
            "error": threading.Event(),
            "connection_closed": threading.Event(),
        }

        self._start_time = time.time()
        self._execution_logs = []
        self._raw_messages = []
        self._pending_request_id = None
        self._pending_input_type = InputType.TEXT
        self._pending_request_at = 0.0
        self._marketing_chunk_buffers = {
            RICH_TYPE_MARKETING_TWEET_REPLY: [],
            RICH_TYPE_MARKETING_TWEET_INTERACT: [],
            RICH_TYPE_WRITER_TWITTER: {},
        }

        def on_message(message):
            self._handle_message(message, result_container, completion_events, options)

        def on_error(error):
            err_msg = f"{type(error).__name__}: {error!r}"
            logger.error(f"WebSocket error: {err_msg}")
            result_container["has_error"] = True
            result_container["error"] = err_msg
            completion_events["error"].set()

        def on_close():
            logger.info("WebSocket connection closed")
            completion_events["connection_closed"].set()

        # Set up handlers
        self.ws_client.set_message_handler(on_message)
        self.ws_client.set_connect_handler(lambda: logger.info("WebSocket connected"))
        self.ws_client.set_disconnect_handler(on_close)
        self.ws_client.set_error_handler(on_error)

        # Connect and start task
        self.ws_client.connect(self.session_info.session_id)
        if not self._wait_until_connected():
            return TaskResult(
                success=False,
                error="Failed to establish WebSocket connection",
                session_duration=time.time() - self._start_time,
            )

        # Start the task
        self._start_task(task, attachments or [], task_mode, extra)

        # Wait for completion
        timeout = options.completion_timeout
        try:
            deadline = time.time() + timeout
            while True:
                self._check_user_input_timeout(options, result_container, completion_events)
                if completion_events["error"].is_set():
                    success = False
                    error = result_container.get("error", "Unknown error")
                    break
                if completion_events["task_completed"].is_set():
                    completed_at = result_container.get("task_completed_at", 0.0)
                    follow_up_received = bool(result_container.get("follow_up_received"))
                    if (
                        follow_up_received
                        or time.time() - completed_at >= FOLLOW_UP_GRACE_SECONDS
                        or completion_events["connection_closed"].is_set()
                    ):
                        success = not result_container.get("stopped", False)
                        error = (
                            "Task was stopped"
                            if result_container.get("stopped")
                            else None
                        )
                        break
                if completion_events["connection_closed"].is_set():
                    success = result_container["task_completed"]
                    error = None if success else "Connection closed before completion"
                    break
                if time.time() >= deadline:
                    success = False
                    error = f"Task timeout after {timeout} seconds"
                    break
                time.sleep(0.05)
        except Exception as e:
            success = False
            error = f"Task execution failed: {str(e)}"
        finally:
            self.ws_client.disconnect()

        return TaskResult(
            success=success,
            final_answer=result_container["final_answer"],
            error=error,
            screenshots=result_container["screenshots"]
            if options.capture_screenshots
            else [],
            execution_logs=[log.model_dump() for log in self._execution_logs]
            if options.event_logging_enabled
            else [],
            plan_history=self._extract_plan_history(),
            session_duration=time.time() - self._start_time,
            message_count=len(self._raw_messages),
        )

    def run_interactive_session(
        self,
        initial_task: str,
        attachments: List[Dict] = None,
        task_mode: TaskMode = TaskMode.Default,
        extra: Optional[Dict[str, Any]] = None,
        options: TaskExecutionOptions = None,
    ) -> None:
        """Run an interactive session with user input support."""
        if options is None:
            options = TaskExecutionOptions()

        result_container = {
            "final_answer": "",
            "task_completed": False,
            "has_error": False,
            "error": None,
            "screenshots": [],
        }

        completion_events = {
            "task_completed": threading.Event(),
            "error": threading.Event(),
            "connection_closed": threading.Event(),
            "user_exit": threading.Event(),
        }

        self._start_time = time.time()
        self._execution_logs = []
        self._raw_messages = []
        self._pending_request_id = None
        self._pending_input_type = InputType.TEXT
        self._pending_request_at = 0.0
        self._marketing_chunk_buffers = {
            RICH_TYPE_MARKETING_TWEET_REPLY: [],
            RICH_TYPE_MARKETING_TWEET_INTERACT: [],
            RICH_TYPE_WRITER_TWITTER: {},
        }

        def on_message(message):
            self._handle_message(message, result_container, completion_events, options)

        def on_error(error):
            err_msg = f"{type(error).__name__}: {error!r}"
            logger.error(f"WebSocket error: {err_msg}")
            result_container["has_error"] = True
            result_container["error"] = err_msg
            completion_events["error"].set()

        def on_close():
            logger.info("WebSocket connection closed")
            completion_events["connection_closed"].set()

        # Set up handlers
        self.ws_client.set_message_handler(on_message)
        self.ws_client.set_connect_handler(lambda: print("✓ WebSocket connected"))
        self.ws_client.set_disconnect_handler(on_close)
        self.ws_client.set_error_handler(on_error)

        # Connect and start task
        self.ws_client.connect(self.session_info.session_id)
        if not self._wait_until_connected():
            detail = result_container.get("error")
            if detail:
                print(f"✗ Failed to connect: {detail}")
            else:
                print("✗ Failed to connect!")
            return

        # Start the task
        self._start_task(initial_task, attachments or [], task_mode, extra)
        print(f"→ Started task: {initial_task}")

        # Interactive loop: only prompt when server requests user input.
        last_idle_debug_at = 0.0
        try:
            while True:
                self._check_user_input_timeout(options, result_container, completion_events)
                # Check for completion
                if completion_events["task_completed"].wait(timeout=0.1):
                    print("✓ Task completed successfully!")
                    break
                elif completion_events["error"].wait(timeout=0.1):
                    print(
                        f"✗ Task execution failed: {result_container.get('error', 'Unknown error')}"
                    )
                    break
                elif completion_events["connection_closed"].wait(timeout=0.1):
                    if not result_container["task_completed"]:
                        print("✗ WebSocket connection closed before task completion")
                    break

                if not self._pending_request_id:
                    if options.verbose:
                        now = time.time()
                        if (
                            now - last_idle_debug_at
                            >= INTERACTIVE_IDLE_DEBUG_INTERVAL_SECONDS
                        ):
                            logger.debug(
                                "waiting for server events "
                                "(pending_request_id=None, task_completed=%s, connection_closed=%s)",
                                completion_events["task_completed"].is_set(),
                                completion_events["connection_closed"].is_set(),
                            )
                            last_idle_debug_at = now
                    time.sleep(0.05)
                    continue

                # Handle user input only when pending request exists
                try:
                    logger.debug(
                        "prompting user input (request_id=%s, input_type=%s)",
                        self._pending_request_id,
                        self._pending_input_type,
                    )
                    prompt = (
                        "[plan] > "
                        if self._pending_input_type == InputType.PLAN
                        else "[input] > "
                    )
                    user_input = input(prompt).strip()

                    if user_input.lower() in ["exit", "quit", "q"]:
                        completion_events["user_exit"].set()
                        break

                    if user_input.lower() == "stop":
                        self.ws_client.send_stop()
                        print("→ Stop command sent")
                        time.sleep(3)
                        continue

                    if user_input.lower() == "pause":
                        self.ws_client.send_pause()
                        print("→ Pause command sent")
                        time.sleep(3)
                        continue

                    if not user_input:
                        print("→ Empty input ignored")
                        continue

                    if self._pending_input_type == InputType.PLAN:
                        resp = WebSocketClient.create_plan_acceptance_response(
                            self._pending_request_id
                        )
                    else:
                        resp = WebSocketClient.create_text_input_response(
                            self._pending_request_id, user_input
                        )
                    self.ws_client.send_message(resp)
                    self._pending_request_id = None
                    self._pending_input_type = InputType.TEXT
                    self._pending_request_at = 0.0
                    print("→ Sent input response")

                except KeyboardInterrupt:
                    print("\nUser interrupted session")
                    completion_events["user_exit"].set()
                    break

        finally:
            logger.debug("interactive loop exited, starting websocket disconnect")
            self.ws_client.disconnect()
            logger.debug("websocket disconnect finished")

            if result_container["final_answer"]:
                print(f"📝 Final Answer: {result_container['final_answer']}")

            if options.capture_screenshots:
                screenshot_count = len(result_container["screenshots"])
                if screenshot_count > 0:
                    print(f"📸 Captured {screenshot_count} screenshots")

            print("Session completed.")

    def _start_task(
        self,
        task: str,
        attachments: List[Dict],
        task_mode: TaskMode,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Start the task execution."""
        data = {
            "messages": [{"type": "task", "content": task}],
            "attachments": attachments,
        }
        if extra:
            data["extra"] = extra
        start_message = {"type": MessageType.START, "data": data}
        self.ws_client.send_message(start_message)

    def _handle_message(
        self,
        message: Dict[str, Any],
        result_container: Dict,
        completion_events: Dict,
        options: TaskExecutionOptions,
    ):
        """Handle incoming WebSocket messages."""
        try:
            msg_type = WebSocketClient.get_message_type(message)
            timestamp = datetime.datetime.now().isoformat()
            if msg_type not in [MessageType.PING, MessageType.PONG]:
                logger.debug(
                    "received message type=%s source=%s message_id=%s",
                    msg_type,
                    message.get("source", ""),
                    message.get("message_id", ""),
                )

            if msg_type == MessageType.TEXT:
                self._handle_text_message(
                    message, result_container, options, timestamp
                )
            elif msg_type == MessageType.PLAN:
                self._handle_plan_message(message, options, timestamp)
            elif msg_type == MessageType.INPUT:
                self._handle_input_message(message, options, timestamp)
            elif msg_type == MessageType.RICH:
                self._handle_rich_message(message, result_container, options, timestamp)
            elif msg_type == MessageType.TASK_RESULT:
                self._handle_task_result(
                    message, result_container, completion_events, options, timestamp
                )
            elif msg_type == MessageType.PROGRESS:
                content = message.get("content", "")
                if options.verbose:
                    print(f"[progress] {content}")
                if options.event_logging_enabled:
                    self._log_event("progress", content, timestamp)
            elif msg_type == MessageType.WARNING:
                pass  # protocol says ignore
            elif msg_type == MessageType.ERROR:
                self._handle_error_message(
                    message, result_container, completion_events, options, timestamp
                )
            elif msg_type not in [MessageType.PING, MessageType.PONG]:
                if options.event_logging_enabled:
                    logger.info(f"Unhandled message type: {msg_type}")

            # Track raw messages for plan acceptance logic
            if msg_type not in [MessageType.PING, MessageType.PONG]:
                self._raw_messages.append(message)

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            if options.event_logging_enabled:
                self._log_event(
                    "error",
                    f"Message handling error: {str(e)}",
                    timestamp,
                    {"error": str(e)},
                )

    def _handle_text_message(
        self,
        message: Dict,
        result_container: Dict,
        options: TaskExecutionOptions,
        timestamp: str,
    ):
        """Handle text messages from agents."""
        content = message.get("content", "")
        source = message.get("source", "unknown")

        if options.verbose:
            display = self._format_text_for_display(content)
            if display:
                print(f"[text] {display}")

        if options.event_logging_enabled:
            self._log_event(source, content, timestamp)

    @staticmethod
    def _format_text_for_display(content: str) -> Optional[str]:
        """Format text content for CLI display. Parse JSON completion messages to show reason."""
        stripped = content.strip()
        # Handle ```json ... ``` wrapped content
        if stripped.startswith("```json") and stripped.endswith("```"):
            stripped = stripped[7:-3].strip()
        if stripped.startswith("{"):
            try:
                obj = json.loads(stripped)
                reason = (obj.get("is_current_step_complete") or {}).get("reason")
                if reason:
                    return reason
            except _json.JSONDecodeError:
                pass
        return content[:200] if content else None

    def _handle_plan_message(
        self, message: Dict, options: TaskExecutionOptions, timestamp: str
    ):
        """Handle plan messages with automatic acceptance support."""
        try:
            msg_inner = message.get("message", {})
            if isinstance(msg_inner, str):
                msg_inner = {}
            sub_type = msg_inner.get("type", "")
            plan_data = msg_inner.get("data", {})
            if options.verbose:
                if sub_type == PlanType.CREATE_PLAN:
                    steps = plan_data if isinstance(plan_data, list) else []
                    print(f"[plan] create plan, {len(steps)} steps")
                    for step in steps:
                        title = (
                            step.get("title", "")
                            if isinstance(step, dict)
                            else str(step)
                        )
                        if title:
                            print(f"  - {title}")
                elif sub_type == PlanType.UPDATE_TASK_STATUS and isinstance(plan_data, dict):
                    step_id = plan_data.get("id", "")
                    title = plan_data.get("title", "")
                    status = plan_data.get("status", "")
                    print(f'[plan] step {step_id} "{title}" -> {status}')
                elif sub_type == PlanType.UPDATE_PLAN:
                    print("[plan] plan updated")

            if self._plan_state is None:
                self._plan_state = Plan()

            changed = self._plan_state.apply_message(message)
            if changed:
                status = self._plan_state.get_overall_status().value
                if options.verbose:
                    print(f"[plan] status: {status}")
                if options.event_logging_enabled:
                    self._log_event(
                        "plan_manager",
                        f"Plan status: {status}",
                        timestamp,
                        {"plan_data": str(message)},
                    )
        except Exception as e:
            logger.error(f"Failed to process plan: {e}")
            if options.event_logging_enabled:
                self._log_event(
                    "error",
                    f"Plan processing error: {str(e)}",
                    timestamp,
                    {"error": str(e)},
                )

    def _extension_url_for_x_confirm(self) -> Optional[str]:
        """Build mate web extension connection URL."""
        query = urlencode(
            {
                "session-id": self.session_info.session_id,
                "x-api-key": self.client.api_key or "",
            }
        )
        # TODO use production URL later
        return f"https://wyse-mate-webapp.vercel.app/agent/extension?{query}"

    def _handle_input_message(
        self, message: Dict, options: TaskExecutionOptions, timestamp: str
    ):
        """Handle input requests with protocol priority:
        1. message.type == "x_confirm" -> plan acceptance (accepted=true)
        2. last message was plan -> plan acceptance
        3. source == "marketing_analyst" -> store pending_request_id for user input
        4. other -> store pending_request_id for user input
        """
        msg_inner = message.get("message", {})
        if isinstance(msg_inner, str):
            msg_inner = {}
        message_data = msg_inner.get("data", {})
        if isinstance(message_data, str):
            message_data = {}
        request_id = message_data.get("request_id")
        inner_type = msg_inner.get("type", "")

        if not request_id:
            logger.debug(
                "ignored input message without request_id (inner_type=%s)",
                inner_type,
            )
            return
        if options.verbose:
            print(
                f"[input] request_id={request_id}, message.type={inner_type or 'unknown'}"
            )

        # Priority 1: x_confirm -> auto-accept
        if inner_type == "x_confirm":
            if options.stop_on_x_confirm:
                try:
                    self.ws_client.send_stop()
                    self._pending_request_id = None
                    self._pending_input_type = InputType.TEXT
                    self._pending_request_at = 0.0
                    if options.verbose:
                        print("→ x_confirm received, sent stop instead of confirm")
                    logger.info(
                        "x_confirm received, stop command sent (request_id=%s)",
                        request_id,
                    )
                    if options.event_logging_enabled:
                        self._log_event(
                            "system",
                            f"x_confirm stop sent {request_id}",
                            timestamp,
                        )
                except Exception as e:
                    logger.error(f"Failed to send stop on x_confirm {request_id}: {e}")
                return
            try:
                open_url = self._extension_url_for_x_confirm()
                if open_url:
                    try:
                        _open_url(open_url)
                    except Exception as e:
                        logger.warning(
                            "Failed to open browser before x_confirm (url=%s): %s",
                            open_url,
                            e,
                        )
                resp = WebSocketClient.create_x_confirm_response(request_id)
                self.ws_client.send_message(resp)
                self._pending_request_id = None
                self._pending_input_type = InputType.TEXT
                self._pending_request_at = 0.0
                if options.verbose:
                    print("→ Auto-confirmed x_confirm")
                logger.info(f"Auto-confirmed x_confirm {request_id}")
                if options.event_logging_enabled:
                    self._log_event("system", f"Auto-confirmed x_confirm {request_id}", timestamp)
            except Exception as e:
                logger.error(f"Failed to confirm x_confirm {request_id}: {e}")
            return

        # Priority 2: last message was plan -> auto-accept plan
        last_msg_type = None
        last_plan_sub_type = None
        for msg in reversed(self._raw_messages):
            if msg.get("type") == MessageType.PLAN:
                last_msg_type = MessageType.PLAN
                last_plan_sub_type = msg.get("message", {}).get("type", "")
                break
            if msg.get("type") not in [MessageType.PING, MessageType.PONG, MessageType.WARNING]:
                break

        if last_msg_type == MessageType.PLAN and last_plan_sub_type in [
            PlanType.CREATE_PLAN, PlanType.UPDATE_PLAN
        ] and options.auto_accept_plan:
            try:
                resp = WebSocketClient.create_plan_acceptance_response(request_id)
                self.ws_client.send_message(resp)
                self._pending_request_id = None
                self._pending_input_type = InputType.TEXT
                self._pending_request_at = 0.0
                if options.verbose:
                    print("→ Auto-accepted plan")
                logger.info(f"Auto-accepted plan request {request_id}")
                if options.event_logging_enabled:
                    self._log_event("system", f"Auto-accepted plan {request_id}", timestamp)
            except Exception as e:
                logger.error(f"Failed to accept plan {request_id}: {e}")
            return

        # Priority 3 & 4: store pending_request_id for user/marketing_analyst input
        self._pending_request_id = request_id
        if last_msg_type == MessageType.PLAN and last_plan_sub_type in [
            PlanType.CREATE_PLAN, PlanType.UPDATE_PLAN
        ]:
            self._pending_input_type = InputType.PLAN
        else:
            self._pending_input_type = InputType.TEXT
        self._pending_request_at = time.time()
        source = message.get("source", "")
        if options.verbose:
            print(f"[input] waiting for user response (source={source})")
        if options.event_logging_enabled:
            self._log_event(
                "input",
                f"Awaiting user input (source={source}, request_id={request_id}, input_type={self._pending_input_type})",
                timestamp,
            )

    def _handle_rich_message(
        self,
        message: Dict,
        result_container: Dict,
        options: TaskExecutionOptions,
        timestamp: str,
    ):
        """Handle rich media messages."""
        message_data = message.get("message", {})
        if isinstance(message_data, str):
            message_data = {}
        message_type = (message_data.get("type") or "").lower()

        if message_type == RICH_TYPE_FOLLOW_UP_SUGGESTION:
            result_container["follow_up_received"] = True
            if options.event_logging_enabled:
                self._log_event("follow_up", "Follow-up suggestions received", timestamp)
            return

        if message_type in {
            RICH_TYPE_MARKETING_TWEET_REPLY,
            RICH_TYPE_MARKETING_TWEET_INTERACT,
            RICH_TYPE_WRITER_TWITTER,
        }:
            self._handle_marketing_rich_message(
                rich_type=message_type,
                message_data=message_data,
                message=message,
                options=options,
                timestamp=timestamp,
            )
            return
        if message_type == RICH_TYPE_MARKETING_REPORT:
            self._handle_marketing_report(message_data, options, timestamp)
            return
        if message_type == RICH_TYPE_MARKETING_RESEARCH_TWEETS:
            self._handle_marketing_research_tweets(message_data, options, timestamp)
            return

        if message_type == "browser":
            self._handle_browser_message(message, result_container, options, timestamp)
        else:
            rich_content = message.get("content", {})
            if options.capture_screenshots and (
                "screenshot" in str(rich_content) or "browser" in str(rich_content).lower()
            ):
                result_container["screenshots"].append(
                    {"timestamp": timestamp, "data": rich_content}
                )

        # Show browser info
        source = (message.get("source") or message.get("source_type") or "").lower()
        inner_type = (message.get("message", {}).get("type") or "").lower()
        if options.enable_browser_logging and (
            source == "wyse_browser" or inner_type == "browser"
        ):
            self.client.browser.show_info(self.session_info.session_id, message)

    def _handle_marketing_rich_message(
        self,
        rich_type: str,
        message_data: Dict[str, Any],
        message: Dict[str, Any],
        options: TaskExecutionOptions,
        timestamp: str,
    ) -> None:
        is_chunk = message.get("delta") is True and bool(message.get("chunk_id"))
        data = message_data.get("data")

        if is_chunk and data:
            if rich_type == RICH_TYPE_WRITER_TWITTER:
                draft_id = data.get("draft_id")
                if draft_id:
                    writer_map = self._marketing_chunk_buffers[RICH_TYPE_WRITER_TWITTER]
                    current = writer_map.get(draft_id)
                    if current:
                        current["content"] = (
                            f"{current.get('content', '')}{data.get('content', '')}"
                        )
                    else:
                        writer_map[draft_id] = dict(data)
                    if options.verbose:
                        chunk_len = len(data.get("content", "") or "")
                        print(f"  [chunk] {rich_type} {draft_id}: +{chunk_len} chars")
            else:
                self._marketing_chunk_buffers[rich_type].append(data)
                if options.verbose:
                    chunk_count = len(self._marketing_chunk_buffers[rich_type])
                    print(f"  [chunk] {rich_type}: {chunk_count} items")

            if options.event_logging_enabled:
                self._log_event("marketing_chunk", f"{rich_type} chunk received", timestamp)
            return

        if not is_chunk:
            if options.verbose:
                print(f"  [stream end] {rich_type}")
            summary = self._fetch_marketing_full_data(rich_type, options, timestamp)
            if options.verbose:
                if rich_type == RICH_TYPE_MARKETING_TWEET_REPLY:
                    print(f"  [reply] full data: {summary.get('reply', 0)} items")
                elif rich_type == RICH_TYPE_MARKETING_TWEET_INTERACT:
                    print(
                        "  [interact] "
                        f"like={summary.get('like', 0)}, retweet={summary.get('retweet', 0)}"
                    )
                elif rich_type == RICH_TYPE_WRITER_TWITTER:
                    print(f"  [tweet] full data: {summary.get('tweet', 0)} items")
            if rich_type == RICH_TYPE_WRITER_TWITTER:
                self._marketing_chunk_buffers[RICH_TYPE_WRITER_TWITTER] = {}
            else:
                self._marketing_chunk_buffers[rich_type] = []

    def _fetch_marketing_full_data(
        self, rich_type: str, options: TaskExecutionOptions, timestamp: str
    ) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        try:
            if rich_type == RICH_TYPE_MARKETING_TWEET_REPLY:
                data = self.client.session.get_marketing_data(
                    self.session_info.session_id, type="reply"
                )
                summary["reply"] = len(data.get("reply", []))
                if options.event_logging_enabled:
                    self._log_event(
                        "marketing_data", f"reply={summary['reply']}", timestamp
                    )
            elif rich_type == RICH_TYPE_MARKETING_TWEET_INTERACT:
                like_data = self.client.session.get_marketing_data(
                    self.session_info.session_id, type="like"
                )
                retweet_data = self.client.session.get_marketing_data(
                    self.session_info.session_id, type="retweet"
                )
                summary["like"] = len(like_data.get("like", []))
                summary["retweet"] = len(retweet_data.get("retweet", []))
                if options.event_logging_enabled:
                    self._log_event(
                        "marketing_data",
                        f"like={summary['like']}, retweet={summary['retweet']}",
                        timestamp,
                    )
            elif rich_type == RICH_TYPE_WRITER_TWITTER:
                data = self.client.session.get_marketing_data(
                    self.session_info.session_id, type="tweet"
                )
                summary["tweet"] = len(data.get("tweet", []))
                if options.event_logging_enabled:
                    self._log_event(
                        "marketing_data", f"tweet={summary['tweet']}", timestamp
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch marketing data for {rich_type}: {e}")
            if options.event_logging_enabled:
                self._log_event(
                    "marketing_data",
                    f"{rich_type} fetch failed: {e}",
                    timestamp,
                )
        return summary

    def _handle_marketing_report(
        self,
        message_data: Dict[str, Any],
        options: TaskExecutionOptions,
        timestamp: str,
    ) -> None:
        data = message_data.get("data", {})
        if isinstance(data, str):
            data = {}
        product_id = data.get("product_id", "")
        product_name = data.get("product_name", "")
        status = data.get("status", "")
        report_id = data.get("report_id", "")

        if options.verbose:
            print(f"  [report] product: {product_name} ({product_id})")
            if status:
                print(f"  [report] status: {status}")
            if report_id:
                print(f"  [report] report_id: {report_id}")

        if options.event_logging_enabled:
            status_text = status or "unknown"
            self._log_event(
                "marketing_report",
                f"product_id={product_id}, status={status_text}",
                timestamp,
            )

    def _handle_marketing_research_tweets(
        self,
        message_data: Dict[str, Any],
        options: TaskExecutionOptions,
        timestamp: str,
    ) -> None:
        data = message_data.get("data", {})
        if isinstance(data, str):
            data = {}
        query_id = data.get("query_id", "")

        if options.verbose:
            print(f"  [research] query_id: {query_id}")
        if not query_id:
            return

        try:
            tweets = self.client.marketing.get_research_tweets(query_id) or []
            if options.verbose:
                print(f"  [research] matched tweets: {len(tweets)}")
                for i, tweet in enumerate(tweets[:5], start=1):
                    if not isinstance(tweet, dict):
                        continue
                    username = tweet.get("username", "")
                    text = (tweet.get("tweet", "") or "")[:60]
                    likes = tweet.get("favorite_count", 0)
                    print(f'    {i}. @{username}: "{text}..." ({likes} likes)')

            if options.event_logging_enabled:
                self._log_event(
                    "marketing_research",
                    f"query_id={query_id}, total={len(tweets)}",
                    timestamp,
                )
        except Exception as e:
            logger.warning(f"Failed to read research tweets for {query_id}: {e}")
            if options.event_logging_enabled:
                self._log_event(
                    "marketing_research",
                    f"fetch failed: {e}",
                    timestamp,
                )

    def _handle_browser_message(
        self,
        message: Dict,
        result_container: Dict,
        options: TaskExecutionOptions,
        timestamp: str,
    ):
        """Handle browser-specific rich messages."""
        browser_data = message.get("message", {}).get("data", {})
        action = browser_data.get("action", "")
        screenshot = browser_data.get("screenshot", "")
        url = browser_data.get("url", "")

        if options.capture_screenshots and screenshot:
            result_container["screenshots"].append(
                {
                    "timestamp": timestamp,
                    "action": action,
                    "url": url,
                    "screenshot": screenshot,
                }
            )

        if options.event_logging_enabled:
            content_parts = []
            if action:
                content_parts.append(f"Action: {action}")
            if url:
                content_parts.append(f"URL: {url}")
            if screenshot:
                content_parts.append("Screenshot captured")

            content_description = (
                "; ".join(content_parts) if content_parts else "Browser activity"
            )
            self._log_event(
                "browser",
                content_description,
                timestamp,
                {
                    "type": "browser_rich",
                    "action": action,
                    "url": url,
                    "has_screenshot": str(bool(screenshot)),
                },
            )

    def _handle_error_message(
        self,
        message: Dict,
        result_container: Dict,
        completion_events: Dict,
        options: TaskExecutionOptions,
        timestamp: str,
    ):
        """Handle error messages (type='error')."""
        code = message.get("code")
        error = message.get("error", "Unknown error")
        message_id = message.get("message_id", "")
        source = message.get("source", "")

        logger.error(f"Session error: code={code} {error}")
        if options.verbose:
            print(f"[error] code={code} {error}")
        result_container["has_error"] = True
        result_container["error"] = f"[{code}] {error}"
        self._log_event("error", f"code={code} {error}", timestamp, {"message_id": message_id, "source": source})
        completion_events["error"].set()

    def _handle_task_result(
        self,
        message: Dict,
        result_container: Dict,
        completion_events: Dict,
        options: TaskExecutionOptions,
        timestamp: str,
    ):
        """Handle final task result."""
        final_answer = message.get("content", "")
        msg_data = message.get("message", {})
        if isinstance(msg_data, dict):
            status = msg_data.get("data", {}).get("status", "")
        else:
            status = ""

        result_container["final_answer"] = final_answer
        result_container["task_completed"] = True
        result_container["task_completed_at"] = time.time()
        if status == "stopped":
            result_container["stopped"] = True
        if options.verbose:
            label = "stopped" if status == "stopped" else "completed"
            print(f"[task_result] {label}")
        logger.debug("task_result status=%s answer=%s", status or "completed", final_answer[:200])

        if options.event_logging_enabled:
            self._log_event(
                "task_result",
                f"Final Answer: {final_answer}",
                timestamp,
                {"type": "final_result", "status": status},
            )

        completion_events["task_completed"].set()

    def _log_event(
        self, source: str, content: str, timestamp: str, metadata: Dict[str, str] = None
    ):
        """Log a structured event."""
        event = EventLog(
            source=source, content=content, timestamp=timestamp, metadata=metadata or {}
        )
        self._execution_logs.append(event)

    def _extract_plan_history(self) -> List[Dict[str, Any]]:
        """Extract plan change history from logs."""
        plan_history = []
        for log in self._execution_logs:
            if log.source == "plan_manager":
                plan_history.append(log.model_dump())
        return plan_history
