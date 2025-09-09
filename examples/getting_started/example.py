#!/usr/bin/env python3
"""
Example usage of the WyseOS Python SDK.
"""

import os
import time
from typing import Optional

from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config
from wyseos.mate.models import (
    CreateSessionRequest,
    ListOptions,
    SessionInfo,
)
from wyseos.mate.plan import Plan
from wyseos.mate.websocket import MessageType, WebSocketClient


def main():
    """Main example function."""
    # Load configuration from mate.yaml, fallback to manual
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
    task = input("Enter your task: ").strip()
    if not task:
        print("  Error: task is required")
        return

    session_info = session_operations(client, "wyse_mate", task)

    print("\n5. Setting up WebSocket connection")
    websocket_operations(client, session_info, task)


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


def websocket_operations(client: Client, session: SessionInfo, initial_task: str):
    """WebSocket interactive session with complete start-to-stop flow."""

    msg_list = []
    plan_state: Optional[Plan] = None

    def on_message(message):
        msg_type = WebSocketClient.get_message_type(message)
        # print(json.dumps(message, ensure_ascii=False, indent=2))

        if msg_type == MessageType.TEXT:
            content = message.get("content", "")
            source = message.get("source", "unknown")
            print(f"  {source} - {content}")

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
                else:
                    print("Plan message received but no changes applied")
                    print(f"Plan status: {plan_state.get_overall_status().value}")
            except Exception as e:
                print(f"Failed to parse/print plan: {e}")

        elif msg_type == MessageType.INPUT:
            request_id = WebSocketClient.get_request_id(message)
            is_response_plan = (
                bool(msg_list) and msg_list[-1].get("type") == MessageType.PLAN
            )
            if request_id and is_response_plan:
                try:
                    acceptance_message = (
                        WebSocketClient.create_plan_acceptance_response(request_id)
                    )
                    if not ws_client.connected:
                        print("    WebSocket not connected, cannot send message")
                        return
                    ws_client.send_message(acceptance_message)
                    print(f"Auto-accepted plan (ID: {request_id})")
                except Exception as e:
                    print(f"Request ID: {request_id}. Failed to accept plan: {e}")
            else:
                print("Awaiting your input. Type 'exit' to leave the session.")

        elif msg_type == MessageType.RICH:
            print("Browser Message:")
            source = (message.get("source") or message.get("source_type") or "").lower()
            inner_type = (message.get("message", {}).get("type") or "").lower()
            if source == "wyse_browser" or inner_type == "browser":
                client.browser.show_info(session.session_id, message)

        elif msg_type == MessageType.TASK_RESULT:
            content = message.get("content", "")
            print(f"Task result: {content}")

        elif msg_type == MessageType.PONG:
            pass

        else:
            print(f"Unhandled type: {msg_type}")
        if msg_type not in [MessageType.PING, MessageType.PONG]:
            msg_list.append(message)

    ws_client = WebSocketClient(
        base_url=client.base_url,
        api_key=client.api_key,
        session_id=session.session_id,
        heartbeat_interval=30,
    )

    ws_client.set_message_handler(on_message)
    ws_client.set_connect_handler(lambda: print("  ✓ WebSocket connected"))
    ws_client.set_disconnect_handler(lambda: print("  ✗ WebSocket disconnected"))
    ws_client.set_error_handler(lambda e: print(f"  ⚠ WebSocket error: {e}"))

    ws_client.connect(session.session_id)
    time.sleep(5)
    if not ws_client.connected:
        print("  Failed to connect!")
        return

    # Start the task immediately using the provided initial_task
    start_message = {
        "type": MessageType.START,
        "data": {
            "messages": [{"type": "task", "content": initial_task}],
            "attachments": [],
            "team_id": session.team_id,
            "kb_ids": [],
        },
    }
    ws_client.send_message(start_message)
    print(f"  → Started task: {initial_task}")

    current_round = 1
    while True:
        user_input = input(f"[{current_round}] > ").strip()

        if user_input.lower() in ["exit", "quit", "q"]:
            break

        if user_input.lower() == "stop":
            ws_client.send_stop()
            print("  → Stop command sent")
            time.sleep(3)
            continue

        if not user_input:
            time.sleep(5)
            continue

    ws_client.disconnect()
    print("  Session completed.")


if __name__ == "__main__":
    main()
