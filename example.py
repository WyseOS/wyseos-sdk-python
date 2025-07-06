#!/usr/bin/env python3
"""
Example usage of the Mate SDK Python.
"""

import time
import uuid
from typing import Optional

# Import the SDK
from wyse_mate import Client, ClientOptions
from wyse_mate.config import load_default_config
from wyse_mate.models import (
    CreateSessionRequest,
    ListOptions,
)
from wyse_mate.websocket import WebSocketClient


def main():
    """Main example function."""
    print("=== Wyse Mate Python SDK Example ===\n")

    # Try to load configuration from mate.yaml
    try:
        config = load_default_config()
        if config:
            print("Loaded configuration from mate.yaml")
            client = Client(config)
        else:
            print("No mate.yaml found, using default configuration")
            client = Client(ClientOptions())
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Using default configuration")
        client = Client(ClientOptions())

    # various operations
    # print("1. User API Keys Operations")
    # user_operations(client)

    # print("\n2. Team Operations")
    # team_operations(client)

    # print("\n3. Agent Operations")
    # team_id = agent_operations(client, None)

    print("\n4. Session Operations")
    session = session_operations(client, "wyse_mate")

    # print("\n5. Browser Operations")
    # session_id = session.session_id if session else None
    # browser_operations(client, session_id)

    print("\n6. WebSocket Operations")
    websocket_operations(client, session.session_id)

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
        session_req = CreateSessionRequest(team_id=team_id, task="")
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


def browser_operations(client: Client, session_id: Optional[str]):
    """browser-related operations."""

    try:
        # List existing browsers
        print("  Listing browsers...")
        browsers = client.browser.list_browsers(session_id)
        print(f"  Found {browsers.total} browsers")

        if browsers.browsers is not None and len(browsers.browsers) > 0:
            browser = browsers.browsers[0]

            # Get browser details
            print("  Getting browser details...")
            browser_details = client.browser.get_info(browser.browser_id)
            print(f"  Browser status: {browser_details.status}")

            # List browser pages
            print("  Listing browser pages...")
            pages = client.browser.list_browser_pages(browser.browser_id)
            print(f"  Browser has {pages.total} pages")
        else:
            print("  No browsers found or browser list is empty.")

    except Exception as e:
        print(f"  Error in browser operations: {e}")


def websocket_operations(client: Client, session_id: str):
    """WebSocket functionality."""

    try:
        print("  Setting up WebSocket connection...")
        # Message received counter
        message_count = 0

        def on_message(message):
            nonlocal message_count
            message_count += 1
            msg_type = message.get("type", "unknown")
            session_id = message.get("session_id", "N/A")

            print(
                f"  WebSocket received message {message_count} (Type: {msg_type}, SessionID: {session_id}):"
            )

            if msg_type == "text":
                source = message.get("source", "N/A")
                content = message.get("content", "No content")
                print(f"    Source: {source}, Content: {content[:100]}...")
            elif msg_type == "pong":
                timestamp = message.get("timestamp", "N/A")
                print(f"    Pong received at timestamp: {timestamp}")
            elif (
                msg_type == "input"
            ):  # Server sends input messages back for confirmation
                input_type = message.get("data", {}).get("input_type", "N/A")
                content = message.get("content", "No content")
                print(f"    Input type: {input_type}, Content: {content[:100]}...")
            else:
                # For other message types, print the whole message for inspection
                print(f"    Full message: {message}")

        def on_connect():
            print("  WebSocket connected successfully")

        def on_disconnect():
            print("  WebSocket disconnected")

        def on_error(error):
            print(f"  WebSocket error: {error}")

        # Create WebSocket client
        ws_client = WebSocketClient(
            base_url=client.base_url,
            api_key=client.api_key,
            session_id=session_id,
            heartbeat_interval=30,
        )

        # Set event handlers
        ws_client.set_message_handler(on_message)
        ws_client.set_connect_handler(on_connect)
        ws_client.set_disconnect_handler(on_disconnect)
        ws_client.set_error_handler(on_error)

        # Connect
        print("  Connecting to WebSocket...")
        ws_client.connect(session_id)

        # Wait for connection
        time.sleep(5)

        if ws_client.connected:
            print("  WebSocket connected. Starting interactive session...")

            current_round = 1

            # Get initial task from user
            initial_task = input(
                "Enter your initial task (e.g., 'please tell me a joke about weather'): "
            )
            if not initial_task:
                initial_task = "please tell me a joke about weather"
                print(f"No initial task entered, using default: '{initial_task}'")

            # 1. Send 'start' message with user's initial task
            start_message = {
                "type": "start",
                "data": {
                    "messages": [{"type": "task", "content": initial_task}],
                    "attachments": [],
                    "session_round": current_round,
                },
            }
            ws_client.send_message(start_message)
            print("  Sent 'start' message with initial task.")
            time.sleep(60)  # Increased wait time for initial responses

            while True:
                user_input = input(
                    f"[{current_round}] Your message (type 'exit' or 'quit' to end): "
                )
                if user_input.lower() in ["exit", "quit"]:
                    print("Ending interactive session.")
                    break

                current_round += 1
                input_message = {
                    "type": "input",
                    "data": {
                        "input_type": "text",
                        "text": user_input,
                        "request_id": str(uuid.uuid4()),
                        "attachments": [],
                        "session_round": current_round,
                    },
                }
                ws_client.send_message(input_message)
                print(f"  Sent 'input' message for turn {current_round}.")
                time.sleep(60)  # Wait for AI response

            # No explicit 'stop' message is sent, relying on function exit to close connection

        # Disconnect
        print("  Disconnecting WebSocket...")
        ws_client.disconnect()

        print(f"  WebSocket demo completed - received {message_count} messages.")

    except Exception as e:
        print(f"  Error in WebSocket operations: {e}")


if __name__ == "__main__":
    # Run the main example
    main()
