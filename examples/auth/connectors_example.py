#!/usr/bin/env python3
"""
Example: manage X (Twitter) connector accounts.

Demonstrates the three X-connector endpoints on UserService:
  - list_x_accounts()        -> GET /connectors/v1/x/accounts
  - authorize_x_account()    -> POST /connectors/v1/x/accounts/authorize
  - delete_x_account(id)     -> DELETE /connectors/v1/x/accounts/{id}

Requires a valid api_key (or jwt_token) in mate.yaml.
"""

import os
from typing import Optional

from wyseos.mate import Client
from wyseos.mate.config import load_config
from wyseos.mate.errors import APIError


def create_client() -> Optional[Client]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mate.yaml")
    try:
        print(f"Loading config: {config_path}")
        return Client(load_config(config_path))
    except Exception as exc:
        print(f"Failed to load config: {exc}")
        print("Please configure mate.yaml with a valid api_key or jwt_token.")
        return None


def print_menu() -> None:
    print("\n=== X Connector Menu ===")
    print("1) List connected X accounts")
    print("2) Authorize a new / existing X account")
    print("3) Delete a connected X account")
    print("q) Quit")


def do_list(client: Client) -> None:
    try:
        result = client.user.list_x_accounts()
    except APIError as exc:
        print(f"List failed: {exc}")
        return

    if not result.items:
        print("No X accounts are currently connected.")
        return

    print(f"Connected X accounts ({len(result.items)}):")
    for idx, account in enumerate(result.items, start=1):
        print(
            f"  {idx}. connector_id={account.connector_id} "
            f"username=@{account.external_username} "
            f"status={account.status} "
            f"expires_at={account.expires_at}"
        )


def do_authorize(client: Client) -> None:
    target = input(
        "Target credential_id (leave empty to create a new connector): "
    ).strip()
    try:
        resp = client.user.authorize_x_account(
            target_credential_id=target or None,
        )
    except APIError as exc:
        print(f"Authorize failed: {exc}")
        return

    print("Open this URL in a browser to complete the binding:")
    print(resp.auth_url)


def do_delete(client: Client) -> None:
    credential_id = input("credential_id to delete: ").strip()
    if not credential_id:
        print("credential_id is required.")
        return

    try:
        client.user.delete_x_account(credential_id)
    except APIError as exc:
        print(f"Delete failed: {exc}")
        return

    print(f"Deleted X connector {credential_id}.")


def main() -> None:
    client = create_client()
    if not client:
        return

    actions = {
        "1": do_list,
        "2": do_authorize,
        "3": do_delete,
    }

    while True:
        print_menu()
        choice = input("Choose an action: ").strip().lower()
        if choice == "q":
            break
        action = actions.get(choice)
        if action is None:
            print("Unknown option.")
            continue
        action(client)


if __name__ == "__main__":
    main()
