#!/usr/bin/env python3
"""
Simplified Example usage of the WyseOS Python SDK.

This example demonstrates the new simplified task execution interface:
- Clean task execution with TaskRunner
- Configurable options for different use cases
- Streamlined error handling and logging
- Both automated and interactive execution modes
"""

import logging
import os

from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config
from wyseos.mate.models import CreateSessionRequest, ListOptions, SessionInfo
from wyseos.mate.websocket import TaskExecutionOptions, WebSocketClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
                print(
                    "\nPlease enter file paths (separate multiple files with commas):"
                )
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
                            print(
                                f"  ✓ File uploaded successfully: {file_info['name']}"
                            )
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
                    print(
                        f"\n✓ All {len(current_batch_files)} files in this batch uploaded successfully!"
                    )

                    # Ask if user wants to continue uploading more files
                    continue_upload = (
                        input("Do you want to continue uploading more files? (y/n): ")
                        .strip()
                        .lower()
                    )
                    if continue_upload not in ["y", "yes", "1"]:
                        break
                else:
                    print(
                        "\n✗ Some files failed to process, please re-enter file paths"
                    )
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

    task = input("4-2. Enter your task: ").strip()
    if not task:
        print("  Error: task is required")
        return

    session_info = session_operations(client, "wyse_mate", task)

    print("\n5. Task Execution")
    execution_mode = input(
        "Choose execution mode (1: Automated, 2: Interactive): "
    ).strip()

    if execution_mode == "1":
        run_automated_task(client, session_info, task, uploaded_files)
    else:
        run_interactive_session(client, session_info, task, uploaded_files)


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
        f"Created new session: {session_id}, Team ID: {team_id}, Status: {session_details.status}"
    )
    return session_details


def run_automated_task(
    client: Client, session_info: SessionInfo, task: str, uploaded_files: list = None
):
    """Run an automated task execution and return results."""
    print("\n--- Automated Task Execution ---")

    ws_client = WebSocketClient(
        base_url=client.base_url,
        api_key=client.api_key,
        session_id=session_info.session_id,
        heartbeat_interval=30,
    )

    task_runner = ws_client.create_task_runner(client, session_info)

    # Configure options for automated execution
    options = TaskExecutionOptions(
        auto_accept_plan=True,
        capture_screenshots=False,  # Disabled for performance
        enable_browser_logging=True,
        enable_event_logging=True,
        completion_timeout=300,  # 5 minutes
    )

    print(f"Starting task: {task}")
    if uploaded_files:
        print(f"With {len(uploaded_files)} file(s) attached")

    try:
        result = task_runner.run_task(
            task=task,
            team_id=session_info.team_id,
            attachments=uploaded_files or [],
            options=options,
        )

        # Display results
        if result.success:
            print("\n✓ Task completed successfully!")
            print(f"Final Answer: {result.final_answer}")
            print(f"Duration: {result.session_duration:.1f} seconds")
            print(f"Messages processed: {result.message_count}")
            if result.execution_logs:
                print(f"Event logs: {len(result.execution_logs)} entries")
        else:
            print(f"\n✗ Task failed: {result.error}")

    except Exception as e:
        print(f"\n✗ Execution error: {e}")
        logger.error(f"Task execution failed: {e}")


def run_interactive_session(
    client: Client, session_info: SessionInfo, task: str, uploaded_files: list = None
):
    """Run an interactive session with user input support."""
    print("\n--- Interactive Session ---")

    # Ask user about screenshot capture
    capture_choice = (
        input("Enable screenshot capture? (y/n, default: n): ").strip().lower()
    )
    capture_screenshots = capture_choice in ["y", "yes"]

    ws_client = WebSocketClient(
        base_url=client.base_url,
        api_key=client.api_key,
        session_id=session_info.session_id,
        heartbeat_interval=30,
    )

    task_runner = ws_client.create_task_runner(client, session_info)

    # Configure options for interactive session
    options = TaskExecutionOptions(
        auto_accept_plan=True,
        capture_screenshots=capture_screenshots,
        enable_browser_logging=True,
        enable_event_logging=True,
        completion_timeout=600,  # 10 minutes for interactive sessions
    )

    if uploaded_files:
        print(
            f"Starting interactive session with {len(uploaded_files)} file(s) attached"
        )

    try:
        task_runner.run_interactive_session(
            initial_task=task,
            team_id=session_info.team_id,
            attachments=uploaded_files or [],
            options=options,
        )
    except Exception as e:
        print(f"\n✗ Session error: {e}")
        logger.error(f"Interactive session failed: {e}")


if __name__ == "__main__":
    main()
