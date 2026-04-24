#!/usr/bin/env python3
"""
Interactive example: pick how to start authentication.

Both flows are unauthenticated (no api_key / jwt_token required):

  - Email: sends a magic sign-in link via ``UserService.start_email_verification``.
  - X (Twitter): returns the OAuth URL via ``UserService.get_x_oauth_url``.

Copy ``mate.yaml.example`` to ``mate.yaml`` if you want a custom ``base_url``;
credentials in that file are not needed for this script.
"""

from __future__ import annotations

import os

from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config
from wyseos.mate.errors import APIError


def create_client() -> Client:
    """Client without credentials; optional mate.yaml for base_url."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mate.yaml")

    if os.path.exists(config_path):
        print(f"Loading config: {config_path}")
        return Client(load_config(config_path))

    print("No mate.yaml found, using default base_url without credentials.")
    return Client(ClientOptions())


def run_email_flow(client: Client) -> None:
    email = input("Email address: ").strip()
    if not email:
        print("Email is required.")
        return

    invite = input("Invite code (optional, press Enter to skip): ").strip()
    invite_code = invite or None

    try:
        resp = client.user.start_email_verification(
            email=email,
            invite_code=invite_code,
        )
    except APIError as exc:
        print(f"Request failed: {exc}")
        return

    print("\nSign-in link request accepted. Response:")
    print(f"  sign_type:    {resp.sign_type}")
    print(f"  pre_auth_id:  {resp.pre_auth_id}")
    print(
        "\nThe user should open the link in the email to finish sign-in."
    )


def run_twitter_oauth_flow(client: Client) -> None:
    try:
        resp = client.user.get_x_oauth_url()
    except APIError as exc:
        print(f"Request failed: {exc}")
        return

    print("\nX (Twitter) OAuth authorization URL:")
    print(resp.auth_url)
    print(
        "\nOpen the URL in a browser to finish login. The backend redirects to "
        "the configured webapp host."
    )


def print_menu() -> None:
    print("\n=== Choose auth method ===")
    print("1) Email — send verify link for sign-in / sign-up")
    print("2) X (Twitter) — get OAuth login URL")
    print("q) Quit")


def main() -> None:
    client = create_client()

    while True:
        print_menu()
        choice = input("Choice: ").strip().lower()
        if choice == "q":
            break
        if choice == "1":
            run_email_flow(client)
        elif choice == "2":
            run_twitter_oauth_flow(client)
        else:
            print("Unknown option.")


if __name__ == "__main__":
    main()
