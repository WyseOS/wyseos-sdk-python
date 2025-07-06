"""
WebSocket client for the Wyse Mate Python SDK.

This module provides WebSocket connectivity for real-time communication with the Wyse Mate.
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
    ENDPOINT_SESSION_WEBSOCKET,
    WEBSOCKET_HEARTBEAT_INTERVAL,
    WEBSOCKET_MAX_MESSAGE_SIZE,
    WEBSOCKET_PROTOCOL,
)
from .errors import WebSocketError
from .models import UserTaskMessage

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    WebSocket client for real-time communication with the Wyse Mate.

    This client handles WebSocket connections, message sending/receiving,
    and provides callbacks for handling incoming messages.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        session_id: str,
        heartbeat_interval: int = WEBSOCKET_HEARTBEAT_INTERVAL,
        max_message_size: int = WEBSOCKET_MAX_MESSAGE_SIZE,
    ):
        """
        Initialize the WebSocket client.

        Args:
            base_url: Base URL for the WebSocket connection
            api_key: API key for authentication
            session_id: Session ID for the WebSocket connection
            heartbeat_interval: Interval for sending heartbeat messages
            max_message_size: Maximum message size in bytes
        """
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

    def connect(self, session_id: str) -> None:
        """
        Connect to the WebSocket server.

        Args:
            session_id: Session ID to connect to
        """
        self.session_id = session_id

        # Start connection in a separate thread
        self.thread = threading.Thread(target=self._run_connection)
        self.thread.daemon = True
        self.thread.start()

    def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        if self.websocket:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.close(), self.loop
                ).result(timeout=5)
            except Exception as e:
                logger.warning(f"Error closing WebSocket connection: {e}")

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def send_message(self, message: Union[Dict[str, Any], UserTaskMessage]) -> None:
        """
        Send a message through the WebSocket connection.

        Args:
            message: Message to send (dict or UserTaskMessage)

        Raises:
            WebSocketError: If not connected or message sending fails
        """
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

            asyncio.run_coroutine_threadsafe(
                self.websocket.send(message_json), self.loop
            ).result(timeout=10)

        except Exception as e:
            raise WebSocketError(
                f"Failed to send message: {str(e)}", session_id=self.session_id, cause=e
            )

    def _run_connection(self) -> None:
        """Run the WebSocket connection in an event loop."""
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
        """Connect to WebSocket and start listening for messages."""
        try:
            await self._establish_connection()
            # Listen for messages
            await self._listen_for_messages()
        except Exception as e:
            self.is_connected = False
            if self.on_error:
                self.on_error(e)
            raise

    async def _establish_connection(self) -> None:
        """Establish WebSocket connection."""
        # Build WebSocket URL
        ws_url = self._build_websocket_url()

        # Build headers
        headers = {}

        # Connect
        self.websocket = await websockets.connect(
            ws_url,
            additional_headers=headers,
            max_size=self.max_message_size,
            ping_interval=self.heartbeat_interval,
            ping_timeout=10,
        )

        self.is_connected = True

        if self.on_connect:
            self.on_connect()

        logger.info(f"WebSocket connected to {ws_url}")

    async def _send_pong(self) -> None:
        """Send a pong response to the server."""
        pong_message = {"type": "pong", "timestamp": int(time.time() * 1000)}
        try:
            await self.websocket.send(json.dumps(pong_message))
            logger.debug("Sent pong message")
        except Exception as e:
            logger.error(f"Failed to send pong message: {e}")

    async def _listen_for_messages(self) -> None:
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    message_data = json.loads(message)

                    # Handle ping from server, mirroring Go SDK
                    if message_data.get("type") == "ping":
                        await self._send_pong()
                        continue  # Do not pass ping messages to the handler

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
        """Build the WebSocket URL for the session."""
        # Convert HTTP(S) URL to WebSocket URL
        parsed = urlparse(self.base_url)

        if parsed.scheme == "https":
            ws_scheme = "wss"
        elif parsed.scheme == "http":
            ws_scheme = "ws"
        else:
            ws_scheme = WEBSOCKET_PROTOCOL

        ws_base_url = f"{ws_scheme}://{parsed.netloc}"

        # Build endpoint
        endpoint = ENDPOINT_SESSION_WEBSOCKET.format(session_id=self.session_id)

        # Add api_key as query parameter, mirroring Go SDK
        full_url = f"{urljoin(ws_base_url, endpoint)}?api_key={self.api_key}"

        return full_url

    def set_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Set the message handler callback."""
        self.on_message = handler

    def set_connect_handler(self, handler: Callable[[], None]) -> None:
        """Set the connect handler callback."""
        self.on_connect = handler

    def set_disconnect_handler(self, handler: Callable[[], None]) -> None:
        """Set the disconnect handler callback."""
        self.on_disconnect = handler

    def set_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Set the error handler callback."""
        self.on_error = handler

    @property
    def connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.is_connected and self.websocket is not None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
