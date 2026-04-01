#!/usr/bin/env python3
"""
Minimal product analysis example.
"""

import os
from typing import Dict, List

from wyseos.mate import Client
from wyseos.mate.config import load_config
from wyseos.mate.errors import APIError


def create_client() -> Client | None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mate.yaml")
    try:
        print(f"Loading config: {config_path}")
        return Client(load_config(config_path))
    except Exception as exc:
        print(f"Failed to load config: {exc}")
        print("Please configure mate.yaml with a valid api_key or jwt_token.")
        return None


def upload_attachments(client: Client, file_paths: List[str]) -> List[Dict[str, str]]:
    attachments: List[Dict[str, str]] = []
    for file_path in file_paths:
        upload = client.file_upload.upload_file(file_path)
        file_name = (upload.get("file_name") or "").strip()
        file_url = (upload.get("file_url") or "").strip()
        if file_name and file_url:
            # Use upload response as the source of truth for attachments.
            attachments.append({"file_name": file_name, "file_url": file_url})
    return attachments


def main() -> None:
    client = create_client()
    if not client:
        return

    product = input("Enter PRODUCT (name or URL): ").strip()
    if not product:
        print("PRODUCT is required")
        return

    files_raw = input("Attachment file paths (comma separated, optional): ").strip()
    file_paths = [item.strip() for item in files_raw.split(",") if item.strip()]

    attachments = upload_attachments(client, file_paths) if file_paths else None

    def on_poll(attempt: int, status: str) -> None:
        print(f"[poll {attempt}] status={status}")

    try:
        report = client.product.create_and_wait(
            product=product,
            attachments=attachments,
            on_poll=on_poll,
        )
    except APIError as exc:
        print(f"Product analysis failed: {exc}")
        return

    print("\n=== Product Report ===")
    print(f"report_id:          {report.report_id}")
    print(f"product_name:       {report.product_name}")
    print(f"target_description: {report.target_description}")
    print(f"keywords:           {', '.join(report.keywords)}")
    print(f"competitors:        {', '.join(report.competitors)}")
    print(f"related_links:      {', '.join(report.related_links)}")
    if report.user_personas:
        print("\nUser Personas:")
        for i, p in enumerate(report.user_personas, 1):
            print(f"  {i}. {p}")
    if report.recommended_campaigns:
        print("\nRecommended Campaigns:")
        for i, c in enumerate(report.recommended_campaigns, 1):
            print(f"  {i}. {c.name} - {c.description}")


if __name__ == "__main__":
    main()
