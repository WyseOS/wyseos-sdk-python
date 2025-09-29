"""
Task runner: high-level task execution interface.
"""

import datetime
import logging
import platform
import subprocess
import threading
import time
import webbrowser
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .plan import Plan
from .websocket import EventLog, MessageType, WebSocketClient

logger = logging.getLogger(__name__)


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

    # Browser configuration options
    use_existing_browser: bool = (
        True  # Try to use existing browser instance to preserve cookies
    )
    preferred_browser: Optional[str] = (
        None  # "chrome", "safari", "firefox", or None for auto-detect
    )


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

    def run_task(
        self,
        task: str,
        team_id: str,
        attachments: List[Dict] = None,
        task_mode: TaskMode = TaskMode.Default,
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

        # Open local browser for Marketing mode
        if task_mode == TaskMode.Marketing:
            url = "http://localhost:3000"
            try:
                if self._open_browser_smart(url, options):
                    logger.info(f"Opened local browser to {url} for Marketing mode")
                else:
                    # Fallback to standard webbrowser.open()
                    webbrowser.open(url)
                    logger.info(
                        f"Opened browser to {url} for Marketing mode (fallback method)"
                    )
            except Exception as e:
                logger.warning(f"Failed to open local browser for Marketing mode: {e}")

        # Start the task
        self._start_task(task, team_id, attachments or [], task_mode)

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
        task_mode: TaskMode = TaskMode.Default,
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

        # Open local browser for Marketing mode
        if task_mode == TaskMode.Marketing:
            url = "http://localhost:3000"
            try:
                if self._open_browser_smart(url, options):
                    print(f"🌐 Opened local browser to {url} for Marketing mode")
                    logger.info(f"Opened local browser to {url} for Marketing mode")
                else:
                    # Fallback to standard webbrowser.open()
                    webbrowser.open(url)
                    print(
                        f"🌐 Opened browser to {url} for Marketing mode (fallback method)"
                    )
                    logger.info(
                        f"Opened browser to {url} for Marketing mode (fallback method)"
                    )
            except Exception as e:
                print(f"⚠️  Failed to open local browser: {e}")
                logger.warning(f"Failed to open local browser for Marketing mode: {e}")

        # Start the task
        self._start_task(initial_task, team_id, attachments or [], task_mode)
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

                    if user_input.lower() == "pause":
                        self.ws_client.send_pause()
                        print("→ Pause command sent")
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

    def _start_task(
        self, task: str, team_id: str, attachments: List[Dict], task_mode: TaskMode
    ):
        """Start the task execution."""
        start_message = {
            "type": MessageType.START,
            "data": {
                "messages": [{"type": "task", "content": task}],
                "attachments": attachments,
                "team_id": team_id,
                "kb_ids": [],
                "mode": task_mode.value if task_mode else "",
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
            # Send stop command immediately when final answer is received
            try:
                self.ws_client.send_stop()
                logger.info("Stop command sent after final answer")
            except Exception as e:
                logger.warning(f"Failed to send stop command: {e}")
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

    def _open_browser_smart(self, url: str, options: TaskExecutionOptions) -> bool:
        """
        Smart browser opening that tries to use existing browser instances to preserve cookies.

        Args:
            url: URL to open
            options: Task execution options containing browser preferences

        Returns:
            bool: True if successfully opened, False otherwise
        """
        if not options.use_existing_browser:
            # Fall back to standard webbrowser.open()
            try:
                webbrowser.open(url)
                return True
            except Exception:
                return False

        # Platform-specific smart opening
        system = platform.system().lower()

        if system == "darwin":  # macOS
            return self._open_browser_macos(url, options.preferred_browser)
        elif system == "windows":
            return self._open_browser_windows(url, options.preferred_browser)
        elif system == "linux":
            return self._open_browser_linux(url, options.preferred_browser)

        # Universal fallback
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False

    def _open_browser_macos(
        self, url: str, preferred_browser: Optional[str] = None
    ) -> bool:
        """Open URL in existing browser instance on macOS using AppleScript."""
        browsers_to_try = []

        if preferred_browser:
            browsers_to_try.append(preferred_browser.lower())

        # Default browser order for macOS
        browsers_to_try.extend(["chrome", "safari", "firefox", "edge"])

        for browser in browsers_to_try:
            if self._try_open_browser_macos(url, browser):
                return True

        return False

    def _try_open_browser_macos(self, url: str, browser: str) -> bool:
        """Try to open URL in a specific browser on macOS."""
        try:
            if browser == "chrome":
                applescript = f'''
                tell application "Google Chrome"
                    if it is running then
                        if (count of windows) > 0 then
                            tell window 1 to make new tab with properties {{URL:"{url}"}}
                        else
                            make new window with properties {{URL:"{url}"}}
                        end if
                        activate
                        return true
                    end if
                end tell
                '''
            elif browser == "safari":
                applescript = f'''
                tell application "Safari"
                    if it is running then
                        if (count of windows) > 0 then
                            tell window 1 to make new tab with properties {{URL:"{url}"}}
                        else
                            make new document with properties {{URL:"{url}"}}
                        end if
                        activate
                        return true
                    end if
                end tell
                '''
            elif browser == "firefox":
                # Firefox doesn't support AppleScript as well, try command line
                subprocess.run(
                    ["open", "-a", "Firefox", "--args", "--new-tab", url],
                    check=True,
                    timeout=5,
                    capture_output=True,
                )
                return True
            elif browser == "edge":
                applescript = f'''
                tell application "Microsoft Edge"
                    if it is running then
                        if (count of windows) > 0 then
                            tell window 1 to make new tab with properties {{URL:"{url}"}}
                        else
                            make new window with properties {{URL:"{url}"}}
                        end if
                        activate
                        return true
                    end if
                end tell
                '''
            else:
                return False

            if browser in ["chrome", "safari", "edge"]:
                result = subprocess.run(
                    ["osascript", "-e", applescript],
                    check=True,
                    timeout=5,
                    capture_output=True,
                    text=True,
                )

                # Check if the script returned success
                return "true" in result.stdout.lower() or result.returncode == 0

        except Exception as e:
            logger.debug(f"Failed to open {browser} on macOS: {e}")
            return False

        return False

    def _open_browser_windows(
        self, url: str, preferred_browser: Optional[str] = None
    ) -> bool:
        """Open URL in existing browser instance on Windows."""
        browsers_to_try = []

        if preferred_browser:
            browsers_to_try.append(preferred_browser.lower())

        browsers_to_try.extend(["chrome", "edge", "firefox"])

        for browser in browsers_to_try:
            if self._try_open_browser_windows(url, browser):
                return True

        return False

    def _try_open_browser_windows(self, url: str, browser: str) -> bool:
        """Try to open URL in a specific browser on Windows."""
        try:
            if browser == "chrome":
                subprocess.run(
                    ["start", "chrome", "--new-tab", url],
                    shell=True,
                    check=True,
                    timeout=5,
                )
                return True
            elif browser == "edge":
                subprocess.run(
                    ["start", "msedge", "--new-tab", url],
                    shell=True,
                    check=True,
                    timeout=5,
                )
                return True
            elif browser == "firefox":
                subprocess.run(
                    ["start", "firefox", "-new-tab", url],
                    shell=True,
                    check=True,
                    timeout=5,
                )
                return True
        except Exception as e:
            logger.debug(f"Failed to open {browser} on Windows: {e}")
            return False

        return False

    def _open_browser_linux(
        self, url: str, preferred_browser: Optional[str] = None
    ) -> bool:
        """Open URL in existing browser instance on Linux."""
        browsers_to_try = []

        if preferred_browser:
            browsers_to_try.append(preferred_browser.lower())

        browsers_to_try.extend(["chrome", "firefox", "chromium"])

        for browser in browsers_to_try:
            if self._try_open_browser_linux(url, browser):
                return True

        return False

    def _try_open_browser_linux(self, url: str, browser: str) -> bool:
        """Try to open URL in a specific browser on Linux."""
        try:
            if browser == "chrome":
                subprocess.run(
                    ["google-chrome", "--new-tab", url],
                    check=True,
                    timeout=5,
                    capture_output=True,
                )
                return True
            elif browser == "firefox":
                subprocess.run(
                    ["firefox", "-new-tab", url],
                    check=True,
                    timeout=5,
                    capture_output=True,
                )
                return True
            elif browser == "chromium":
                subprocess.run(
                    ["chromium-browser", "--new-tab", url],
                    check=True,
                    timeout=5,
                    capture_output=True,
                )
                return True
        except Exception as e:
            logger.debug(f"Failed to open {browser} on Linux: {e}")
            return False

        return False
