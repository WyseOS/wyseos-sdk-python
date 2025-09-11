"""
WebSocket client
"""

import asyncio
import datetime
import json
import logging
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import websockets
from pydantic import BaseModel

from .constants import (
    DEFAULT_TIMEOUT,
    ENDPOINT_SESSION_WEBSOCKET,
    WEBSOCKET_HEARTBEAT_INTERVAL,
    WEBSOCKET_MAX_MESSAGE_SIZE,
    WEBSOCKET_PROTOCOL,
)
from .errors import WebSocketError
from .models import UserTaskMessage
from .plan import AcceptPlan, Plan

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskExecutionOptions(BaseModel):
    """Configuration options for task execution."""

    auto_accept_plan: bool = True
    capture_screenshots: bool = (
        False  # Default off to avoid unnecessary resource consumption
    )
    enable_browser_logging: bool = True
    enable_event_logging: bool = True  # Control detailed execution event logging
    completion_timeout: int = 300  # 5 minutes
    max_user_input_timeout: int = 0  # User input timeout, 0 means infinite wait


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


class EventLog(BaseModel):
    """Structured event log for operations."""

    source: str
    content: str
    timestamp: str
    metadata: Dict[str, str] = {}


class MessageType:
    TEXT = "text"
    PLAN = "plan"
    INPUT = "input"
    RICH = "rich"
    PING = "ping"
    PONG = "pong"
    START = "start"
    PAUSE = "pause"
    STOP = "stop"
    TASK_RESULT = "task_result"


class PlanType:
    CREATE_PLAN = "create_plan"
    UPDATE_TASK_STATUS = "update_task_status"


class InputType:
    TEXT = "text"
    PLAN = "plan"


class WebSocketClient:
    """WebSocket client for real-time communication with the WyseOS."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        session_id: str,
        heartbeat_interval: int = WEBSOCKET_HEARTBEAT_INTERVAL,
        max_message_size: int = WEBSOCKET_MAX_MESSAGE_SIZE,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.session_id = session_id
        self.heartbeat_interval = heartbeat_interval
        self.max_message_size = max_message_size

        self.websocket = None
        self.is_connected = False

        # Event handlers
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

        # Threading
        self.loop = None
        self.thread = None
        self._heartbeat_task = None

    @staticmethod
    def get_message_type(message: Dict[str, Any]) -> str:
        return message.get("type", "unknown")

    @staticmethod
    def safe_json_parse(json_str: str) -> Dict[str, Any]:
        if not isinstance(json_str, str):
            return {}
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def get_request_id(message: Dict[str, Any]) -> Optional[str]:
        message_payload = message.get("message", {})
        if isinstance(message_payload, str):
            message_payload = WebSocketClient.safe_json_parse(message_payload)
        message_data = message_payload.get("data", {})
        return message_data.get("request_id")

    @staticmethod
    def create_plan_acceptance_response(
        request_id: str, plan: Optional[list] = None
    ) -> Dict[str, Any]:
        accept = AcceptPlan.create(accepted=True, plan=plan or [], content="")
        return {
            "type": MessageType.INPUT,
            "data": {
                "input_type": InputType.PLAN,
                "request_id": request_id,
                "response": accept.model_dump(exclude_none=True),
            },
        }

    def connect(self, session_id: str) -> None:
        self.session_id = session_id
        self.thread = threading.Thread(target=self._run_connection)
        self.thread.daemon = True
        self.thread.start()

    def disconnect(self) -> None:
        if self._heartbeat_task and self.loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._stop_heartbeat(), self.loop
                ).result(timeout=DEFAULT_TIMEOUT)
            except Exception as e:
                logger.warning(f"Error stopping heartbeat: {e}")

        if self.websocket:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.close(), self.loop
                ).result(timeout=DEFAULT_TIMEOUT)
            except Exception as e:
                logger.warning(f"Error closing WebSocket connection: {e}")

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=DEFAULT_TIMEOUT)

    def send_message(self, message: Union[Dict[str, Any], UserTaskMessage]) -> None:
        if not self.is_connected or not self.websocket:
            raise WebSocketError(
                "WebSocket is not connected", session_id=self.session_id
            )

        if isinstance(message, UserTaskMessage):
            message_dict = message.dict()
        else:
            message_dict = message

        try:
            message_json = json.dumps(message_dict)
            if len(message_json) > self.max_message_size:
                raise WebSocketError(
                    f"Message size ({len(message_json)}) exceeds maximum ({self.max_message_size})",
                    session_id=self.session_id,
                )

            # If we're in the same event loop thread, schedule send without blocking to avoid deadlock
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if self.loop and current_loop is self.loop:
                asyncio.create_task(self.websocket.send(message_json))
            else:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(message_json), self.loop
                ).result(timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            raise WebSocketError(
                f"Failed to send message: {str(e)}", session_id=self.session_id, cause=e
            )

    def send_ping(self) -> None:
        if not self.is_connected or not self.websocket:
            raise WebSocketError(
                "WebSocket is not connected", session_id=self.session_id
            )

        try:
            # Avoid blocking when called from within the event loop thread
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if self.loop and current_loop is self.loop:
                asyncio.create_task(self._send_ping())
            else:
                asyncio.run_coroutine_threadsafe(self._send_ping(), self.loop).result(
                    timeout=DEFAULT_TIMEOUT
                )
        except Exception as e:
            raise WebSocketError(
                f"Failed to send ping: {str(e)}", session_id=self.session_id, cause=e
            )

    def send_stop(self) -> None:
        if not self.is_connected or not self.websocket:
            raise WebSocketError(
                "WebSocket is not connected", session_id=self.session_id
            )

        stop_message = {"type": MessageType.STOP}
        try:
            # Avoid blocking when called from within the event loop thread
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if self.loop and current_loop is self.loop:
                asyncio.create_task(self.websocket.send(json.dumps(stop_message)))
            else:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps(stop_message)), self.loop
                ).result(timeout=DEFAULT_TIMEOUT)
            logger.info("Sent stop command")
        except Exception as e:
            raise WebSocketError(
                f"Failed to send stop command: {str(e)}",
                session_id=self.session_id,
                cause=e,
            )

    def _run_connection(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._connect_and_listen())
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            if self.on_error:
                self.on_error(e)
        finally:
            self.loop.close()

    async def _connect_and_listen(self) -> None:
        try:
            await self._establish_connection()
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            await self._listen_for_messages()
        except Exception as e:
            self.is_connected = False
            if self.on_error:
                self.on_error(e)
            raise
        finally:
            await self._stop_heartbeat()

    async def _establish_connection(self) -> None:
        ws_url = self._build_websocket_url()

        self.websocket = await websockets.connect(
            ws_url,
            max_size=self.max_message_size,
            ping_interval=None,
            ping_timeout=None,
        )

        self.is_connected = True

        if self.on_connect:
            self.on_connect()

        logger.info(f"WebSocket connected to {ws_url}")

    async def _send_ping(self) -> None:
        ping_message = {"type": MessageType.PING, "timestamp": int(time.time() * 1000)}
        try:
            await self.websocket.send(json.dumps(ping_message))
        except Exception as e:
            logger.error(f"Failed to send ping message: {e}")
            raise

    async def _send_pong(self) -> None:
        pong_message = {"type": MessageType.PONG, "timestamp": int(time.time() * 1000)}
        try:
            await self.websocket.send(json.dumps(pong_message))
        except Exception as e:
            logger.error(f"Failed to send pong message: {e}")

    async def _heartbeat_loop(self) -> None:
        try:
            while self.is_connected and self.websocket:
                await asyncio.sleep(self.heartbeat_interval)
                if self.is_connected and self.websocket:
                    await self._send_ping()
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")
            if self.on_error:
                self.on_error(e)

    async def _stop_heartbeat(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

    async def _listen_for_messages(self) -> None:
        try:
            async for message in self.websocket:
                try:
                    message_data = json.loads(message)

                    if message_data.get("type") == MessageType.PING:
                        await self._send_pong()
                        continue

                    if message_data.get("type") == MessageType.PONG:
                        if self.on_message:
                            self.on_message(message_data)
                        continue

                    if self.on_message:
                        self.on_message(message_data)

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse WebSocket message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.is_connected = False

            if self.on_disconnect:
                self.on_disconnect()

        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
            raise

    def _build_websocket_url(self) -> str:
        parsed = urlparse(self.base_url)

        if parsed.scheme == "https":
            ws_scheme = "wss"
        elif parsed.scheme == "http":
            ws_scheme = "ws"
        else:
            ws_scheme = WEBSOCKET_PROTOCOL

        ws_base_url = f"{ws_scheme}://{parsed.netloc}"
        endpoint = ENDPOINT_SESSION_WEBSOCKET.format(session_id=self.session_id)
        full_url = f"{urljoin(ws_base_url, endpoint)}?api_key={self.api_key}"

        return full_url

    def set_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self.on_message = handler

    def set_connect_handler(self, handler: Callable[[], None]) -> None:
        self.on_connect = handler

    def set_disconnect_handler(self, handler: Callable[[], None]) -> None:
        self.on_disconnect = handler

    def set_error_handler(self, handler: Callable[[Exception], None]) -> None:
        self.on_error = handler

    @property
    def connected(self) -> bool:
        return self.is_connected and self.websocket is not None

    def create_task_runner(self, client, session_info) -> "TaskRunner":
        """Create a task runner for high-level task execution."""
        return TaskRunner(self, client, session_info)


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

    def run_task(
        self,
        task: str,
        team_id: str,
        attachments: List[Dict] = None,
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

        def on_message(message):
            self._handle_message(message, result_container, completion_events, options)

        def on_error(error):
            logger.error(f"WebSocket error: {error}")
            result_container["has_error"] = True
            result_container["error"] = str(error)
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
        time.sleep(2)  # Allow connection to establish

        if not self.ws_client.connected:
            return TaskResult(
                success=False,
                error="Failed to establish WebSocket connection",
                session_duration=time.time() - self._start_time,
            )

        # Start the task
        self._start_task(task, team_id, attachments or [])

        # Wait for completion
        timeout = options.completion_timeout
        try:
            if completion_events["task_completed"].wait(timeout=timeout):
                success = True
                error = None
            elif completion_events["error"].wait(timeout=0.1):
                success = False
                error = result_container.get("error", "Unknown error")
            elif completion_events["connection_closed"].wait(timeout=0.1):
                success = result_container["task_completed"]
                error = None if success else "Connection closed before completion"
            else:
                success = False
                error = f"Task timeout after {timeout} seconds"
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
            if options.enable_event_logging
            else [],
            plan_history=self._extract_plan_history(),
            session_duration=time.time() - self._start_time,
            message_count=len(self._raw_messages),
        )

    def run_interactive_session(
        self,
        initial_task: str,
        team_id: str,
        attachments: List[Dict] = None,
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

        def on_message(message):
            self._handle_message(message, result_container, completion_events, options)

        def on_error(error):
            logger.error(f"WebSocket error: {error}")
            result_container["has_error"] = True
            result_container["error"] = str(error)
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
        time.sleep(2)

        if not self.ws_client.connected:
            print("✗ Failed to connect!")
            return

        # Start the task
        self._start_task(initial_task, team_id, attachments or [])
        print(f"→ Started task: {initial_task}")

        # Interactive loop
        current_round = 1
        try:
            while True:
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

                # Handle user input
                try:
                    user_input = input(f"[{current_round}] > ").strip()
                    current_round += 1

                    if user_input.lower() in ["exit", "quit", "q"]:
                        completion_events["user_exit"].set()
                        break

                    if user_input.lower() == "stop":
                        self.ws_client.send_stop()
                        print("→ Stop command sent")
                        time.sleep(3)
                        continue

                    if user_input:
                        user_message = {"type": MessageType.TEXT, "content": user_input}
                        self.ws_client.send_message(user_message)
                        print(f"→ Sent: {user_input}")

                except KeyboardInterrupt:
                    print("\nUser interrupted session")
                    completion_events["user_exit"].set()
                    break

        finally:
            self.ws_client.disconnect()

            if result_container["final_answer"]:
                print(f"📝 Final Answer: {result_container['final_answer']}")

            if options.capture_screenshots:
                screenshot_count = len(result_container["screenshots"])
                if screenshot_count > 0:
                    print(f"📸 Captured {screenshot_count} screenshots")

            print("Session completed.")

    def _start_task(self, task: str, team_id: str, attachments: List[Dict]):
        """Start the task execution."""
        start_message = {
            "type": MessageType.START,
            "data": {
                "messages": [{"type": "task", "content": task}],
                "attachments": attachments,
                "team_id": team_id,
                "kb_ids": [],
            },
        }
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

            if msg_type == MessageType.TEXT:
                self._handle_text_message(
                    message, result_container, completion_events, options, timestamp
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
            elif msg_type not in [MessageType.PING, MessageType.PONG]:
                if options.enable_event_logging:
                    logger.info(f"Unhandled message type: {msg_type}")

            # Track raw messages for plan acceptance logic
            if msg_type not in [MessageType.PING, MessageType.PONG]:
                self._raw_messages.append(message)

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            if options.enable_event_logging:
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
        completion_events: Dict,
        options: TaskExecutionOptions,
        timestamp: str,
    ):
        """Handle text messages from agents."""
        content = message.get("content", "")
        source = message.get("source", "unknown")

        if options.enable_event_logging:
            self._log_event(source, content, timestamp)

        # Check for final answer
        message_metadata = message.get("message", {}).get("metadata", {})
        if message_metadata.get("type") == "final_answer":
            result_container["final_answer"] = content
            result_container["task_completed"] = True
            logger.info(f"Final answer received: {content}")
            completion_events["task_completed"].set()

    def _handle_plan_message(
        self, message: Dict, options: TaskExecutionOptions, timestamp: str
    ):
        """Handle plan messages with automatic acceptance support."""
        try:
            if self._plan_state is None:
                self._plan_state = Plan()

            changed = self._plan_state.apply_message(message)
            if changed and options.enable_event_logging:
                status = self._plan_state.get_overall_status().value
                self._log_event(
                    "plan_manager",
                    f"Plan status: {status}",
                    timestamp,
                    {"plan_data": str(message)},
                )
                logger.info(f"Plan updated: {status}")
        except Exception as e:
            logger.error(f"Failed to process plan: {e}")
            if options.enable_event_logging:
                self._log_event(
                    "error",
                    f"Plan processing error: {str(e)}",
                    timestamp,
                    {"error": str(e)},
                )

    def _handle_input_message(
        self, message: Dict, options: TaskExecutionOptions, timestamp: str
    ):
        """Handle input requests including plan confirmations."""
        message_data = message.get("message", {}).get("data", {})
        request_id = message_data.get("request_id")
        message_type = message.get("message", {}).get("type", "")
        is_text_input = message_type == "text"

        # Check for plan request
        recent_plan_message = None
        for msg in reversed(self._raw_messages):
            if msg.get("type") == "plan":
                recent_plan_message = msg
                break

        is_plan_request = False
        if recent_plan_message:
            plan_msg_type = recent_plan_message.get("message", {}).get("type", "")
            is_plan_request = plan_msg_type in ["create_plan", "update_plan"]

        if (
            request_id
            and is_plan_request
            and is_text_input
            and options.auto_accept_plan
        ):
            try:
                acceptance = {
                    "type": "input",
                    "data": {
                        "input_type": "plan",
                        "request_id": request_id,
                        "response": {
                            "accepted": True,
                            "plan": [],
                            "content": "",
                        },
                    },
                }
                self.ws_client.send_message(acceptance)
                logger.info(f"Auto-accepted plan request {request_id}")

                if options.enable_event_logging:
                    self._log_event(
                        "system",
                        f"Auto-accepted plan request {request_id}",
                        timestamp,
                        {"request_id": request_id},
                    )
            except Exception as e:
                logger.error(f"Failed to accept plan {request_id}: {e}")

    def _handle_rich_message(
        self,
        message: Dict,
        result_container: Dict,
        options: TaskExecutionOptions,
        timestamp: str,
    ):
        """Handle rich media messages including browser screenshots."""
        message_data = message.get("message", {})
        message_type = message_data.get("type", "").lower()

        if message_type == "browser":
            self._handle_browser_message(message, result_container, options, timestamp)
        else:
            # Handle other rich content
            rich_content = message.get("content", {})
            if options.capture_screenshots and (
                "screenshot" in rich_content or "browser" in str(rich_content).lower()
            ):
                result_container["screenshots"].append(
                    {"timestamp": timestamp, "data": rich_content}
                )

        # Show browser info
        source = (message.get("source") or message.get("source_type") or "").lower()
        inner_type = (message.get("message", {}).get("type") or "").lower()
        if source == "wyse_browser" or inner_type == "browser":
            self.client.browser.show_info(self.session_info.session_id, message)

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

        if options.enable_event_logging:
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
        result_container["final_answer"] = final_answer
        result_container["task_completed"] = True
        logger.info(f"Task completed: {final_answer}")

        if options.enable_event_logging:
            self._log_event(
                "task_result",
                f"Final Answer: {final_answer}",
                timestamp,
                {"type": "final_result"},
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
