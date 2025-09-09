"""
WebSocket client
"""

import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Union
from urllib.parse import urljoin, urlparse

import websockets

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
