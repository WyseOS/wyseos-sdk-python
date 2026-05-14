"""
WebSocket client
"""

import asyncio
import concurrent.futures
import json
import logging
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union
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
from .plan import AcceptPlan

logger = logging.getLogger(__name__)

WEBSOCKET_CLOSE_TIMEOUT_SECONDS = 2.0
WEBSOCKET_SHUTDOWN_TIMEOUT_SECONDS = 3.0
WEBSOCKET_THREAD_JOIN_TIMEOUT_SECONDS = 3.0


def _ws_netloc(parsed) -> str:
    host = parsed.hostname or ""
    if host == "localhost":
        host = "127.0.0.1"
    if parsed.port:
        return f"{host}:{parsed.port}"
    return host


def _is_benign_disconnect_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, concurrent.futures.TimeoutError)):
        return True
    if isinstance(exc, (asyncio.CancelledError, concurrent.futures.CancelledError)):
        return True
    if isinstance(exc, RuntimeError) and "Event loop is closed" in str(exc):
        return True
    return False


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
    PROGRESS = "progress"
    WARNING = "warning"
    ERROR = "error"


class PlanType:
    CREATE_PLAN = "create_plan"
    UPDATE_PLAN = "update_plan"
    UPDATE_TASK_STATUS = "update_task_status"


class InputType:
    TEXT = "text"
    PLAN = "plan"


class WebSocketClient:
    """WebSocket client for real-time communication."""

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        session_id: str = "",
        jwt_token: str = "",
        heartbeat_interval: int = WEBSOCKET_HEARTBEAT_INTERVAL,
        max_message_size: int = WEBSOCKET_MAX_MESSAGE_SIZE,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.jwt_token = jwt_token
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

    @staticmethod
    def create_text_input_response(
        request_id: str,
        text: str,
        attachments: Optional[list] = None,
        skills: Optional[list] = None,
    ) -> Dict[str, Any]:
        return {
            "type": MessageType.INPUT,
            "data": {
                "input_type": InputType.TEXT,
                "text": text,
                "request_id": request_id,
                "attachments": attachments or [],
                "skills": skills or [],
            },
        }

    @staticmethod
    def create_x_confirm_response(
        request_id: str, content: str = ""
    ) -> Dict[str, Any]:
        # x_confirm uses input_type="plan" with accepted=true per protocol section 2c
        return {
            "type": MessageType.INPUT,
            "data": {
                "input_type": InputType.PLAN,
                "request_id": request_id,
                "response": {"accepted": True, "content": content},
            },
        }

    def connect(self, session_id: str) -> None:
        self.session_id = session_id
        self.thread = threading.Thread(target=self._run_connection)
        self.thread.daemon = True
        self.thread.start()

    def disconnect(self) -> None:
        started_at = time.time()
        logger.debug("disconnect requested (session_id=%s)", self.session_id)
        self.is_connected = False

        close_future = None
        if self.loop and not self.loop.is_closed():
            try:
                close_future = asyncio.run_coroutine_threadsafe(
                    self._shutdown_connection(),
                    self.loop,
                )
                close_future.result(timeout=WEBSOCKET_SHUTDOWN_TIMEOUT_SECONDS)
            except Exception as e:
                if _is_benign_disconnect_error(e):
                    logger.debug("WebSocket shutdown timed out during disconnect")
                else:
                    logger.warning("Error during WebSocket shutdown: %s", e)
                if close_future:
                    close_future.cancel()
                self._abort_websocket_transport()
        elif self.websocket:
            self._abort_websocket_transport()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=WEBSOCKET_THREAD_JOIN_TIMEOUT_SECONDS)
            if self.thread.is_alive():
                self._request_loop_stop()
                self.thread.join(timeout=WEBSOCKET_THREAD_JOIN_TIMEOUT_SECONDS)
                if self.thread.is_alive():
                    logger.warning("websocket thread still alive after join timeout")

        self.websocket = None
        self._heartbeat_task = None
        self.loop = None
        self.thread = None
        logger.debug("disconnect finished in %.2fs", time.time() - started_at)

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
            self._schedule_send(message_json, "message")
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
            self._schedule_background_coroutine(self._send_ping(), "ping")
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
            self._schedule_send(json.dumps(stop_message), "stop")
            logger.info("Sent stop command")
        except Exception as e:
            raise WebSocketError(
                f"Failed to send stop command: {str(e)}",
                session_id=self.session_id,
                cause=e,
            )

    def send_pause(self) -> None:
        if not self.is_connected or not self.websocket:
            raise WebSocketError(
                "WebSocket is not connected", session_id=self.session_id
            )

        pause_message = {"type": MessageType.PAUSE}
        try:
            self._schedule_send(json.dumps(pause_message), "pause")
            logger.info("Sent pause command")
        except Exception as e:
            raise WebSocketError(
                f"Failed to send pause command: {str(e)}",
                session_id=self.session_id,
                cause=e,
            )

    def _schedule_send(self, payload: str, action: str) -> None:
        async def _send() -> None:
            await self.websocket.send(payload)

        self._schedule_background_coroutine(_send(), action)

    def _schedule_background_coroutine(self, coro, action: str) -> None:
        if not self.loop or self.loop.is_closed():
            raise WebSocketError(
                "WebSocket event loop is unavailable",
                session_id=self.session_id,
            )

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop is self.loop:
            task = asyncio.create_task(coro)
            task.add_done_callback(lambda future: self._consume_future_error(future, action))
            return

        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        future.add_done_callback(lambda done: self._consume_future_error(done, action))

    def _consume_future_error(self, future, action: str) -> None:
        try:
            future.result()
        except Exception as exc:
            if _is_benign_disconnect_error(exc):
                logger.debug("WebSocket %s aborted during shutdown", action)
                return
            logger.warning("WebSocket %s failed: %s", action, exc)
            if self.on_error:
                self.on_error(exc)

    def _request_loop_stop(self) -> None:
        if not self.loop or self.loop.is_closed():
            return
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception as exc:
            logger.debug("Failed to stop event loop: %s", exc)

    def _abort_current_transport(self) -> None:
        if not self.websocket:
            return
        transport = getattr(self.websocket, "transport", None)
        if transport is None:
            return
        try:
            transport.abort()
            logger.info("WebSocket transport aborted")
        except Exception as exc:
            logger.warning("Failed to abort WebSocket transport: %s", exc)

    def _abort_websocket_transport(self) -> None:
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.call_soon_threadsafe(self._abort_current_transport)
                return
            except Exception as exc:
                logger.debug("Failed to schedule WebSocket transport abort: %s", exc)
        self._abort_current_transport()

    def _run_connection(self) -> None:
        loop = asyncio.new_event_loop()
        self.loop = loop
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._connect_and_listen())
        except Exception as e:
            logger.exception(
                "WebSocket connection error (%s): %r",
                type(e).__name__,
                e,
            )
            if self.on_error:
                self.on_error(e)
        finally:
            try:
                loop.close()
            finally:
                if self.loop is loop:
                    self.loop = None

    async def _connect_and_listen(self) -> None:
        try:
            await self._establish_connection()
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            await self._listen_for_messages()
        except Exception as e:
            self.is_connected = False
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

        logger.debug(f"WebSocket connected to {ws_url}")

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

    async def _shutdown_connection(self) -> None:
        await self._stop_heartbeat()
        if not self.websocket:
            return
        try:
            await asyncio.wait_for(
                self.websocket.close(),
                timeout=WEBSOCKET_CLOSE_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            if _is_benign_disconnect_error(exc):
                logger.debug("WebSocket close timed out during shutdown")
            else:
                logger.warning("WebSocket close failed during shutdown: %s", exc)
        if not getattr(self.websocket, "closed", False):
            self._abort_current_transport()

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

        ws_base_url = f"{ws_scheme}://{_ws_netloc(parsed)}"
        endpoint = ENDPOINT_SESSION_WEBSOCKET.format(session_id=self.session_id)
        if self.jwt_token:
            full_url = f"{urljoin(ws_base_url, endpoint)}?authorization={self.jwt_token}"
        else:
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
