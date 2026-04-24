#!/usr/bin/env python3
"""
Example: fetch the X (Twitter) OAuth login URL.

This endpoint is called *before* the user has any credentials, so it does
not require an api_key or jwt_token — the client is constructed with the
default options.
"""

import os

from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config
from wyseos.mate.errors import APIError


def create_client() -> Client:
    """Return a Client. Credentials are optional for this endpoint."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mate.yaml")

    if os.path.exists(config_path):
        print(f"Loading config: {config_path}")
        return Client(load_config(config_path))

    print("No mate.yaml found, using default base_url without credentials.")
    return Client(ClientOptions())


def main() -> None:
    client = create_client()

    try:
        resp = client.user.get_x_oauth_url()
    except APIError as exc:
        print(f"Request failed: {exc}")
        return

    print("X OAuth authorization URL:")
    print(resp.auth_url)
    print(
        "\nOpen the URL in a browser to complete the login flow. The backend "
        "will redirect to the configured webapp host."
    )


if __name__ == "__main__":
    main()
