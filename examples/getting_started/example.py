#!/usr/bin/env python3
"""
Enhanced Example usage of the WyseOS Python SDK.

This enhanced example demonstrates comprehensive message handling capabilities including:
- Structured event logging with Pydantic models
- Automatic plan acceptance with intelligent logic
- Rich message processing for browser interactions
- Screenshot and content capture
- Completion tracking with threading events

The message handling logic is inspired by the automatic_wyseos_sdk.py implementation
but adapted to work directly with the SDK's internal classes and components.
"""

import datetime
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config
from wyseos.mate.models import (
    CreateSessionRequest,
    ListOptions,
    SessionInfo,
)
from wyseos.mate.plan import Plan
from wyseos.mate.websocket import MessageType, WebSocketClient

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EventLog(BaseModel):
    """
    Logging events during operations.

    Attributes:
        source (str): The source of the event (e.g., agent name).
        content (str): The content/message of the event.
        timestamp (str): ISO-formatted timestamp of the event.
        metadata (Dict[str, str]): Additional metadata for the event.
    """

    source: str
    content: str
    timestamp: str
    metadata: Dict[str, str] = {}


def main():
    """Main example function."""
    # Load configuration from mate.yaml
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "mate.yaml")
        client = Client(load_config(config_path))
        print("Loaded configuration from mate.yaml")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        client = Client(ClientOptions())
        print("Using default configuration")

    print("1. User API Keys")
    user_operations(client)

    print("\n2. Teams")
    team_operations(client)

    print("\n3. Agents")
    agent_operations(client)

    print("\n4. Start New Session")
    print("\n4-1. File Upload (Optional)")

    upload_choice = input("Do you have files to upload? (y/n): ").strip().lower()

    uploaded_files = []
    if upload_choice == "y" or upload_choice == "yes":
        while True:
            try:
                print("\nPlease enter file paths (separate multiple files with commas):")
                file_paths_input = input("File paths: ").strip()

                if not file_paths_input:
                    print("  ✗ Please enter valid file paths")
                    continue

                # Split multiple file paths
                file_paths = [
                    path.strip() for path in file_paths_input.split(",") if path.strip()
                ]

                if not file_paths:
                    print("  ✗ Please enter valid file paths")
                    continue

                all_success = True
                current_batch_files = []

                for file_path in file_paths:
                    print(f"\nProcessing file: {file_path}")

                    # Validate file
                    is_valid, message = client.file_upload.validate_file(file_path)
                    if is_valid:
                        print(f"  ✓ File validation passed: {message}")

                        # Upload file
                        print("  Uploading file...")

                        file_info = client.file_upload.get_file_info(file_path)

                        upload_result = client.file_upload.upload_file(file_path)

                        if upload_result.get("file_url"):
                            file_info = client.file_upload.get_file_info(file_path)
                            file_data = {
                                "file_name": file_info["name"],
                                "file_url": upload_result.get("file_url", ""),
                            }
                            current_batch_files.append(file_data)
                            print(f"  ✓ File uploaded successfully: {file_info['name']}")
                        else:
                            print(
                                f"  ✗ File upload failed: {upload_result.get('error', 'Unknown error')}"
                            )
                            all_success = False
                    else:
                        print(f"  ✗ File validation failed: {message}")
                        all_success = False

                if all_success and current_batch_files:
                    uploaded_files.extend(current_batch_files)
                    print(f"\n✓ All {len(current_batch_files)} files in this batch uploaded successfully!")

                    # Ask if user wants to continue uploading more files
                    continue_upload = (
                        input("Do you want to continue uploading more files? (y/n): ").strip().lower()
                    )
                    if continue_upload not in ["y", "yes", "1"]:
                        break
                else:
                    print("\n✗ Some files failed to process, please re-enter file paths")
                    retry = input("Do you want to retry? (y/n): ").strip().lower()
                    if retry not in ["y", "yes", "1"]:
                        break

            except Exception as e:
                print(f"  ✗ Error occurred during file upload: {e}")
                retry = input("Do you want to retry? (y/n): ").strip().lower()
                if retry not in ["y", "yes", "1"]:
                    break

        if uploaded_files:
            print(f"\n📁 Total {len(uploaded_files)} files uploaded successfully:")
            for file_data in uploaded_files:
                print(f"  - {file_data['file_name']}")

    task = input("4-2.Enter your task: ").strip()
    if not task:
        print("  Error: task is required")
        return

    session_info = session_operations(client, "wyse_mate", task)

    print("\n5. Setting up WebSocket connection")
    websocket_operations(
        client,
        session_info,
        task,
        auto_accept_plan=True,
        uploaded_files=uploaded_files,
    )


def user_operations(client: Client):
    """User-related operations."""

    api_keys_page = client.user.list_api_keys(ListOptions(page_num=1, page_size=10))
    print(f"  Found {api_keys_page.total} API keys")
    for key in api_keys_page.data:
        print(f"    - {key.name}")


def team_operations(client: Client):
    """Team-related operations."""

    teams_page = client.team.get_list("all", ListOptions(page_num=1, page_size=10))
    print(f"  Found {teams_page.total} teams")
    for team in teams_page.data:
        print(f"    - {team.name} (ID: {team.team_id})")


def agent_operations(client: Client):
    """Agent-related operations."""

    agents_page = client.agent.get_list("all", ListOptions(page_num=1, page_size=10))
    print(f"  Found {agents_page.total} agents")
    for agent in agents_page.data:
        print(f"    - {agent.name} (ID: {agent.agent_id})")


def session_operations(client: Client, team_id: str, task: str) -> SessionInfo:
    """Create a session and fetch its info."""

    create_resp = client.session.create(
        CreateSessionRequest(team_id=team_id, task=task)
    )
    session_id = create_resp.session_id
    session_details = client.session.get_info(session_id)
    print(
        f"  Created new session: {session_id}, Team ID: {team_id}, Status: {session_details.status}"
    )
    return session_details


def websocket_operations(
    client: Client,
    session: SessionInfo,
    initial_task: str,
    auto_accept_plan: bool = True,
    uploaded_files: list = None,
):
    """WebSocket interactive session with comprehensive message handling."""

    messages_so_far: List[EventLog] = []
    raw_messages: List[Dict[str, Any]] = []
    plan_state: Optional[Plan] = None
    result_container = {
        "final_answer": "",
        "task_completed": False,
        "has_error": False,
        "error": None,
        "connection_closed": False,
        "screenshots": [],
    }

    # Create completion events for thread-safe communication
    completion_events = {
        "task_completed": threading.Event(),
        "error": threading.Event(),
        "connection_closed": threading.Event(),
        "user_exit": threading.Event(),
    }

    def on_message(message):
        try:
            msg_type = WebSocketClient.get_message_type(message)
            timestamp = datetime.datetime.now().isoformat()

            if msg_type == MessageType.TEXT:
                # Handle text messages from agents
                raw_metadata = message.get("metadata", {})
                str_metadata = {k: str(v) for k, v in raw_metadata.items()}
                content = message.get("content", "")
                source = message.get("source", "unknown")

                log_event = EventLog(
                    source=source,
                    content=content,
                    timestamp=timestamp,
                    metadata=str_metadata,
                )
                messages_so_far.append(log_event)
                print(f"  {source} - {content}")

                # Check if this is a final answer message based on metadata
                message_metadata = message.get("message", {}).get("metadata", {})
                if message_metadata.get("type") == "final_answer":
                    final_answer = content
                    result_container["final_answer"] = final_answer
                    result_container["task_completed"] = True
                    logger.info(f"Final answer from TEXT message: {final_answer}")

                    result_log = EventLog(
                        source="task_result",
                        content=f"Final Answer from TEXT: {final_answer}",
                        timestamp=timestamp,
                        metadata={"type": "final_result_from_text"},
                    )
                    messages_so_far.append(result_log)

                    # Set completion event
                    completion_events["task_completed"].set()

            elif msg_type == MessageType.PLAN:
                try:
                    nonlocal plan_state
                    if plan_state is None:
                        plan_state = Plan()
                    changed = plan_state.apply_message(message)
                    if changed:
                        print("Received Plan:")
                        print(plan_state.render_text())
                        print(f"Plan status: {plan_state.get_overall_status().value}")

                        # Log plan state
                        plan_log = EventLog(
                            source="plan_manager",
                            content=f"Plan status: {plan_state.get_overall_status().value}",
                            timestamp=timestamp,
                            metadata={"plan_data": str(message)},
                        )
                        messages_so_far.append(plan_log)
                    else:
                        print("Plan message received but no changes applied")
                        print(f"Plan status: {plan_state.get_overall_status().value}")
                except Exception as e:
                    print(f"Failed to parse/print plan: {e}")
                    error_log = EventLog(
                        source="error",
                        content=f"Plan processing error: {str(e)}",
                        timestamp=timestamp,
                        metadata={"error": str(e)},
                    )
                    messages_so_far.append(error_log)

            elif msg_type == MessageType.INPUT:
                # Enhanced plan auto-acceptance logic
                message_data = message.get("message", {}).get("data", {})
                request_id = message_data.get("request_id")

                # Check if this is a text-type input message
                message_type = message.get("message", {}).get("type", "")
                is_text_input = message_type == "text"

                # Look for the most recent plan message to check if it's a plan request
                recent_plan_message = None
                for msg in reversed(raw_messages):
                    if msg.get("type") == "plan":
                        recent_plan_message = msg
                        break

                # Check if the recent plan message is either create_plan or update_plan
                is_plan_request = False
                if recent_plan_message:
                    plan_msg_type = recent_plan_message.get("message", {}).get(
                        "type", ""
                    )
                    is_plan_request = plan_msg_type in ["create_plan", "update_plan"]

                if (
                    request_id
                    and is_plan_request
                    and is_text_input
                    and auto_accept_plan
                ):
                    try:
                        # Create acceptance message
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

                        if not ws_client.connected:
                            print(
                                "    WebSocket not connected, cannot send plan acceptance"
                            )
                            return
                        ws_client.send_message(acceptance)
                        print(f"Auto-accepted plan request {request_id}")

                        accept_log = EventLog(
                            source="system",
                            content=f"Auto-accepted plan request {request_id}",
                            timestamp=timestamp,
                            metadata={"request_id": request_id},
                        )
                        messages_so_far.append(accept_log)
                    except Exception as e:
                        logger.error(
                            f"Request ID: {request_id}. Failed to accept plan: {e}"
                        )
                        error_log = EventLog(
                            source="error",
                            content=f"Failed to accept plan: {str(e)}",
                            timestamp=timestamp,
                            metadata={"request_id": request_id, "error": str(e)},
                        )
                        messages_so_far.append(error_log)
                else:
                    print("Awaiting your input. Type 'exit' to leave the session.")

            elif msg_type == MessageType.RICH:
                # Enhanced RICH message handling
                message_data = message.get("message", {})
                message_type = message_data.get("type", "").lower()

                if message_type == "browser":
                    # Handle browser-type RICH messages
                    browser_data = message_data.get("data", {})
                    action = browser_data.get("action", "")
                    screenshot = browser_data.get("screenshot", "")
                    text = browser_data.get("text", "")
                    url = browser_data.get("url", "")

                    # Create comprehensive content description
                    content_parts = []
                    if action:
                        content_parts.append(f"Action: {action}")
                    if url:
                        content_parts.append(f"URL: {url}")
                    if text:
                        content_parts.append(
                            f"Text: {text[:200]}..."
                            if len(text) > 200
                            else f"Text: {text}"
                        )
                    if screenshot:
                        content_parts.append("Screenshot captured")

                    content_description = (
                        "; ".join(content_parts)
                        if content_parts
                        else "Browser activity"
                    )

                    # Store screenshot data if present
                    if screenshot:
                        result_container["screenshots"].append(
                            {
                                "timestamp": timestamp,
                                "action": action,
                                "url": url,
                                "screenshot": screenshot,
                            }
                        )

                    # Log the browser message
                    browser_log = EventLog(
                        source="browser",
                        content=content_description,
                        timestamp=timestamp,
                        metadata={
                            "type": "browser_rich",
                            "action": action,
                            "url": url,
                            "text": text,
                            "has_screenshot": str(bool(screenshot)),
                            "raw_data": str(browser_data),
                        },
                    )
                    messages_so_far.append(browser_log)
                    print(f"Browser: {content_description}")

                    # Show browser info using the client
                    source = (
                        message.get("source") or message.get("source_type") or ""
                    ).lower()
                    inner_type = (message.get("message", {}).get("type") or "").lower()
                    if source == "wyse_browser" or inner_type == "browser":
                        client.browser.show_info(session.session_id, message)

                else:
                    # Handle other RICH message types
                    rich_content = message.get("content", {})
                    if (
                        "screenshot" in rich_content
                        or "browser" in str(rich_content).lower()
                    ):
                        result_container["screenshots"].append(
                            {"timestamp": timestamp, "data": rich_content}
                        )

                        screenshot_log = EventLog(
                            source="rich_content",
                            content="Rich content with screenshot",
                            timestamp=timestamp,
                            metadata={"type": "screenshot", "data": str(rich_content)},
                        )
                        messages_so_far.append(screenshot_log)
                    else:
                        # Log other RICH messages
                        rich_log = EventLog(
                            source="rich_content",
                            content=f"RICH message type: {message_type}",
                            timestamp=timestamp,
                            metadata={
                                "type": "rich_other",
                                "message_type": message_type,
                                "raw_message": str(message),
                            },
                        )
                        messages_so_far.append(rich_log)

            elif msg_type == MessageType.TASK_RESULT:
                # Handle final task result
                final_answer = message.get("content", "")
                result_container["final_answer"] = final_answer
                result_container["task_completed"] = True
                print(f"Task result: {final_answer}")
                logger.info(f"Received final answer: {final_answer}")

                result_log = EventLog(
                    source="task_result",
                    content=f"Final Answer: {final_answer}",
                    timestamp=timestamp,
                    metadata={"type": "final_result"},
                )
                messages_so_far.append(result_log)

                # Set completion event
                completion_events["task_completed"].set()

            elif msg_type == MessageType.PONG:
                pass

            else:
                if msg_type != MessageType.PING:
                    print(f"Unhandled message type: {msg_type}")
                    generic_log = EventLog(
                        source="websocket",
                        content=f"Message type: {msg_type}",
                        timestamp=timestamp,
                        metadata={
                            "message_type": str(msg_type),
                            "raw_message": str(message),
                        },
                    )
                    messages_so_far.append(generic_log)

            # Track raw messages for plan acceptance logic (exclude PING/PONG)
            if msg_type not in [MessageType.PING, MessageType.PONG]:
                raw_messages.append(message)

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            error_log = EventLog(
                source="error",
                content=f"WebSocket message handling error: {str(e)}",
                timestamp=datetime.datetime.now().isoformat(),
                metadata={"error": str(e)},
            )
            messages_so_far.append(error_log)

    def on_error(error):
        logger.error(f"WebSocket error: {error}")
        result_container["has_error"] = True
        result_container["error"] = str(error)
        completion_events["error"].set()

    def on_close():
        logger.info("WebSocket connection closed")
        result_container["connection_closed"] = True
        completion_events["connection_closed"].set()

    ws_client = WebSocketClient(
        base_url=client.base_url,
        api_key=client.api_key,
        session_id=session.session_id,
        heartbeat_interval=30,
    )

    ws_client.set_message_handler(on_message)
    ws_client.set_connect_handler(lambda: print("  ✓ WebSocket connected"))
    ws_client.set_disconnect_handler(on_close)
    ws_client.set_error_handler(on_error)

    ws_client.connect(session.session_id)
    time.sleep(5)
    if not ws_client.connected:
        print("  Failed to connect!")
        return

    # Start the task immediately using the provided initial_task+
    # # Use uploaded files from main function
    attachments = uploaded_files if uploaded_files else []
    # Start the task with optional file attachments

    start_message = {
        "type": MessageType.START,
        "data": {
            "messages": [{"type": "task", "content": initial_task}],
            "attachments": attachments,
            "team_id": session.team_id,
            "kb_ids": [],
        },
    }
    ws_client.send_message(start_message)
    if attachments:
        print(f"  → Started task with {len(attachments)} attachment(s): {initial_task}")
    else:
        print(f"  → Started task: {initial_task}")

    current_round = 1
    try:
        while True:
            # Check for completion
            if completion_events["task_completed"].wait(timeout=0.1):
                print("  ✓ Task completed successfully!")
                break
            elif completion_events["error"].wait(timeout=0.1):
                print(
                    f"  ✗ Task execution failed: {result_container.get('error', 'Unknown error')}"
                )
                break
            elif completion_events["connection_closed"].wait(timeout=0.1):
                if not result_container["task_completed"]:
                    print("  ✗ WebSocket connection closed before task completion")
                break

            # Non-blocking input check
            try:
                user_input = input(f"[{current_round}] > ").strip()
                current_round += 1

                if user_input.lower() in ["exit", "quit", "q"]:
                    completion_events["user_exit"].set()
                    break

                if user_input.lower() == "stop":
                    ws_client.send_stop()
                    print("  → Stop command sent")
                    time.sleep(3)
                    continue

                if not user_input:
                    time.sleep(1)
                    continue

                # Send user message
                user_message = {"type": MessageType.TEXT, "content": user_input}
                ws_client.send_message(user_message)
                print(f"  → Sent: {user_input}")

            except KeyboardInterrupt:
                print("\n  User interrupted session")
                completion_events["user_exit"].set()
                break

    finally:
        ws_client.disconnect()

        if result_container["final_answer"]:
            print(f"  📝 Final Answer: {result_container['final_answer']}")

        screenshot_count = len(result_container["screenshots"])
        if screenshot_count > 0:
            print(f"  📸 Captured {screenshot_count} screenshots")

        print("  Session completed.")


if __name__ == "__main__":
    main()
