"""
File upload service for the WyseOS SDK Python.
"""

import os
import mimetypes
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from pathlib import Path

import requests

from ..constants import (
    DEFAULT_TIMEOUT,
    HEADER_API_KEY,
    HEADER_USER_AGENT,
)
from ..errors import APIError

if TYPE_CHECKING:
    from ..client import Client


class FileUploadService:
    """File upload service class

    Provides file selection, validation and upload functionality.
    """

    # Supported file types
    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".md",
        ".csv",
        ".html",
        ".htm",
        ".rss",
        ".xml",
        ".gif",
        ".py",
        ".json",
    }

    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, client: "Client"):
        """Initialize file upload service

        Args:
            client: Main API client instance
        """
        self.client = client

    def select_file(self, prompt: str = "Please enter file path: ") -> Optional[str]:
        """Interactive file selection

        Args:
            prompt: Prompt message

        Returns:
            Optional[str]: Selected file path, returns None if cancelled
        """
        while True:
            file_path = input(prompt).strip()

            if not file_path:
                print("No file selected")
                return None

            if file_path.lower() in ["cancel", "quit", "exit", "q"]:
                print("File selection cancelled")
                return None

            # Expand user directory
            file_path = os.path.expanduser(file_path)

            if not os.path.exists(file_path):
                print(f"File does not exist: {file_path}")
                continue

            if not os.path.isfile(file_path):
                print(f"Path is not a file: {file_path}")
                continue

            # Validate file
            validation_result = self.validate_file(file_path)
            if not validation_result[0]:
                print(f"File validation failed: {validation_result[1]}")
                continue

            return file_path

    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """Validate if file meets upload requirements

        Args:
            file_path: File path

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            path = Path(file_path)

            # Check if file exists
            if not path.exists():
                return False, "File does not exist"

            if not path.is_file():
                return False, "Path is not a file"

            # Check file extension
            if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                return False, f"Unsupported file type: {path.suffix}"

            # Check file size
            file_size = path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return (
                    False,
                    f"File too large: {file_size / 1024 / 1024:.1f}MB (max: {self.MAX_FILE_SIZE / 1024 / 1024}MB)",
                )

            if file_size == 0:
                return False, "File is empty"

            return True, "File validation passed"

        except Exception as e:
            return False, f"File validation error: {str(e)}"

    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """Get file information

        Args:
            file_path: File path

        Returns:
            Dict[str, any]: File information
        """
        path = Path(file_path)
        file_size = path.stat().st_size
        mime_type, _ = mimetypes.guess_type(file_path)

        return {
            "name": path.name,
            "size": file_size,
            "extension": path.suffix.lower(),
            "mime_type": mime_type or "application/octet-stream",
            "path": str(path.absolute()),
        }

    def upload_file(
        self, file_path: str, session_id: Optional[str] = None
    ) -> Dict[str, any]:
        """Upload file to server

        Args:
            file_path: File path
            session_id: Session ID (optional)

        Returns:
            Dict[str, any]: Upload result

        Raises:
            APIError: Raised when upload fails
        """
        # Validate file
        validation_result = self.validate_file(file_path)
        if not validation_result[0]:
            raise APIError(f"File validation failed: {validation_result[1]}")

        file_info = self.get_file_info(file_path)

        try:
            # Prepare upload data
            with open(file_path, "rb") as f:
                files = {"files": (file_info["name"], f, file_info["mime_type"])}

                data = {}
                if session_id:
                    data["session_id"] = session_id

                headers = {
                    HEADER_USER_AGENT: self.client.user_agent,
                }

                if self.client.api_key:
                    headers[HEADER_API_KEY] = self.client.api_key

                # 注意：使用multipart/form-data时不要手动设置Content-Type
                # requests会自动设置正确的Content-Type和boundary

                upload_url = f"{self.client.base_url}/session/upload"

                response = requests.post(
                    upload_url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self.client.timeout or DEFAULT_TIMEOUT,
                )

                if response.status_code != 200:
                    raise APIError(
                        f"File upload failed: HTTP {response.status_code}",
                        status_code=response.status_code,
                    )

                result = response.json()

                # Check API response
                if result.get("code") != 0:
                    raise APIError(
                        f"File upload failed: {result.get('msg', 'Unknown error')}",
                        code=result.get("code"),
                    )

                upload_result = result.get("data", [])

                return {
                    "file_url": upload_result[0].get("file_url"),
                    "file_name": file_info["name"],
                }

        except requests.exceptions.RequestException as e:
            raise APIError(f"Network error: {str(e)}")
        except Exception as e:
            raise APIError(f"Upload failed: {str(e)}")

    def list_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions

        Returns:
            List[str]: Supported file extensions
        """
        return sorted(list(self.SUPPORTED_EXTENSIONS))

    def format_file_size(self, size_bytes: int) -> str:
        """Format file size display

        Args:
            size_bytes: File size in bytes

        Returns:
            str: Formatted file size
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / 1024 / 1024:.1f} MB"
