"""
Factory module for creating SDK components.
This module helps avoid circular imports between websocket and task_runner.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .task_runner import TaskRunner
    from .websocket import WebSocketClient


def create_task_runner(
    ws_client: "WebSocketClient", client, session_info
) -> "TaskRunner":
    """Create a task runner for high-level task execution.

    Args:
        ws_client: WebSocket client instance
        client: API client instance
        session_info: Session information

    Returns:
        TaskRunner instance
    """
    from .task_runner import TaskRunner

    return TaskRunner(ws_client, client, session_info)
