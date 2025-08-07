#!/usr/bin/env python3
"""
Example usage of the Mate SDK Python.
"""

import time
import uuid
from typing import Optional

# Import the SDK
from wyse_mate import Client, ClientOptions
from wyse_mate.config import load_config
from wyse_mate.models import (
    CreateSessionRequest,
    ListOptions,
    SessionInfo,
)
from wyse_mate.websocket import MessageType, WebSocketClient


def main():
    """Main example function."""
    print("=== Wyse Mate Python SDK Example ===\n")

    # Try to load configuration from mate.yaml
    try:
        print("Loaded configuration from mate.yaml")
        client = Client(load_config())
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Using default configuration")
        client = Client(ClientOptions())

    # various operations
    # print("1. User API Keys Operations")
    # user_operations(client)

    print("\n2. Team Operations")
    team_operations(client)

    # print("\n3. Agent Operations")
    # team_id = agent_operations(client, None)

    print("\n4. Session Operations")
    session = session_operations(client, "wyse_mate")

    # print("\n5. Browser Operations")
    # session_id = session.session_id if session else None
    # browser_operations(client, session_id)

    print("\n5. WebSocket Operations")
    websocket_operations(client, session)

    print("\n=== Example completed ===")


def user_operations(client: Client):
    """user-related operations."""

    try:
        # List API keys
        print("  Listing API keys...")
        api_keys_page = client.user.list_api_keys(ListOptions(page_num=1, page_size=10))
        print(f"  Found {api_keys_page.total} API keys")

        for key in api_keys_page.data[:3]:  # Show first 3
            print(f"    - {key.name} (ID: {key.id})")

    except Exception as e:
        print(f"  Error in user operations: {e}")


def team_operations(client: Client):
    """team-related operations."""

    try:
        # List teams
        print("  Listing teams...")
        teams_page = client.team.get_list("all", ListOptions(page_num=1, page_size=10))
        print(f"  Found {teams_page.total} teams")

        for team in teams_page.data[:3]:  # Show first 3
            print(f"    - {team.name} (ID: {team.team_id})")

        # Get team details
        if teams_page.data:
            print(f"  Getting details for team: {teams_page.data[0].name}")
            team_details = client.team.get_info(teams_page.data[0].team_id)
            print(f"    Team type: {team_details.team_type}")
            print(f"    Description: {team_details.description}")

    except Exception as e:
        print(f"  Error in team operations: {e}")


def agent_operations(client: Client, team_id: Optional[str]):
    """agent-related operations."""

    try:
        # List agents
        print("  Listing agents...")
        agents_page = client.agent.get_list(
            "all", ListOptions(page_num=1, page_size=10)
        )
        print(f"  Found {agents_page.total} agents")

        for agent in agents_page.data[:3]:  # Show first 3
            print(f"    - {agent.name} (ID: {agent.agent_id})")

        # Get agent details
        if agents_page.data:
            print(f"  Getting details for agent: {agents_page.data[0].name}")
            agent_details = client.agent.get_info(agents_page.data[0].agent_id)
            print(f"    Agent type: {agent_details.agent_type}")
            print(f"    Description: {agent_details.description}")

        return agents_page.data[0].agent_id if agents_page.data else None

    except Exception as e:
        print(f"  Error in agent operations: {e}")
        return None


def session_operations(client: Client, team_id: str):
    """session-related operations (session list removed, only create/get/info/messages)."""

    try:
        print("  Creating a new session...")
        session_req = CreateSessionRequest(
            team_id=team_id, task="tell me a joke about Rust language"
        )
        create_resp = client.session.create(session_req)
        session_id = create_resp.session_id
        print(f"  Created new session: {session_id}")

        # Get session details
        print("  Getting session details...")
        session_details = client.session.get_info(session_id)
        print(f"  Session status: {session_details.status}")

        return session_details
    except Exception as e:
        print(f"  Error in session operations: {e}")
        return None


def websocket_operations(client: Client, session: SessionInfo):
    """WebSocket interactive session with complete start-to-stop flow."""

    def print_browser_info():
        """Print current browser information."""
        try:
            browsers = client.browser.list_browsers(session.session_id)
            if browsers.browsers and len(browsers.browsers) > 0:
                browser = browsers.browsers[0]
                browser_details = client.browser.get_info(browser.browser_id)
                pages = client.browser.list_browser_pages(browser.browser_id)
                print(f"    Browser: {browser_details.status} | Pages: {pages.total}")
            else:
                print("    Browser: None active")
        except Exception:
            print("    Browser: Error retrieving info")

    try:
        print("  Setting up WebSocket connection...")
        message_count = 0

        def on_message(message):
            nonlocal message_count
            message_count += 1

            msg_type = WebSocketClient.get_message_type(message)
            print(f"  [{message_count}] {msg_type.upper()}: ", end="")

            # Print browser info for non-control messages
            should_print_browser = msg_type not in [
                MessageType.PLAN,
                MessageType.PING,
                MessageType.PONG,
            ]

            if msg_type == MessageType.TEXT:
                content = message.get("content", "")[:100]
                source = message.get("source", "unknown")
                print(f"{source} - {content}...")
                if should_print_browser:
                    print_browser_info()

            elif msg_type == MessageType.PLAN:
                content = message.get("content", "")
                print(f"{content}")

            elif msg_type == MessageType.INPUT:
                print(f"    WebSocket connected: {ws_client.connected}")
                request_id = WebSocketClient.get_request_id(message)
                print(f"    Extracted request_id: {request_id}")

                if request_id:
                    try:
                        acceptance_message = (
                            WebSocketClient.create_plan_acceptance_response(request_id)
                        )
                        print(f"    Generated acceptance message: {acceptance_message}")

                        # Check message format
                        try:
                            import json

                            message_json = json.dumps(acceptance_message)
                            print(f"    Message JSON length: {len(message_json)}")
                        except Exception as json_error:
                            print(f"    JSON serialization error: {json_error}")
                            return

                        if not ws_client.connected:
                            print("    WebSocket not connected, cannot send message")
                            return

                        ws_client.send_message(acceptance_message)
                        print(f"Auto-accepted plan (ID: {request_id[:8]}...)")
                    except Exception as e:
                        print(f"Failed to accept plan: {e}")
                        print(f"Request ID: {request_id}")
                        print(f"Message keys: {list(message.keys())}")
                        print(f"Message.message: {message.get('message', 'NOT_FOUND')}")
                        import traceback

                        traceback.print_exc()
                else:
                    print("Input request (no ID)")
                    print(f"Message keys: {list(message.keys())}")
                    print(f"Message.message: {message.get('message', 'NOT_FOUND')}")
                if should_print_browser:
                    print_browser_info()

            elif msg_type == MessageType.RICH:
                action = (
                    message.get("message", {}).get("data", {}).get("action", "unknown")
                )
                print(f"Browser action: {action}")
                if should_print_browser:
                    print_browser_info()

            elif msg_type == MessageType.TASK_RESULT:
                content = message.get("content", "")
                print(f"Task result: {content}")
                if should_print_browser:
                    print_browser_info()

            elif msg_type == MessageType.PONG:
                print("Heartbeat response")

            else:
                print(f"Unhandled type: {msg_type}")
                if should_print_browser:
                    print_browser_info()

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

        print("  Connecting...")
        ws_client.connect(session.session_id)
        time.sleep(3)

        if not ws_client.connected:
            print("  Failed to connect!")
            return

        print("  ✓ Ready for interaction")
        current_round = 1

        initial_task = input("Enter your task: ").strip()
        if not initial_task:
            initial_task = "tell me a joke"

        start_message = {
            "type": MessageType.START,
            "data": {
                "messages": [{"type": "task", "content": initial_task}],
                "attachments": [],
                "team_id": session.team_id,
                "session_round": current_round,
            },
        }
        ws_client.send_message(start_message)
        print(f"  → Started task: {initial_task}")
        time.sleep(5)

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

            current_round += 1
            input_message = {
                "type": MessageType.INPUT,
                "data": {
                    "input_type": "text",
                    "text": user_input,
                    "request_id": str(uuid.uuid4()),
                    "attachments": [],
                    "session_round": current_round,
                },
            }
            ws_client.send_message(input_message)
            print(f"  → Sent: {user_input}")
            time.sleep(5)

        ws_client.disconnect()
        print(f"  Session completed ({message_count} messages)")

    except Exception as e:
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the main example
    main()
