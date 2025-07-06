"""
User service for the Mate SDK Python.

This module contains the UserService class for user-related API operations.
"""

from typing import TYPE_CHECKING, Optional

from ..constants import (
    ENDPOINT_API_KEY_LIST,
)
from ..models import (
    APIKey,
    ListOptions,
    PaginatedResponse,
)

if TYPE_CHECKING:
    from ..client import Client


class UserService:
    """
    Service for user-related API operations.

    This service provides methods for managing user API keys.
    """

    def __init__(self, client: "Client"):
        """
        Initialize the user service.

        Args:
            client: The main API client instance
        """
        self.client = client

    def list_api_keys(
        self, options: Optional[ListOptions] = None
    ) -> PaginatedResponse[APIKey]:
        """
        List API keys for the current user.

        Args:
            options: Optional pagination options

        Returns:
            PaginatedResponse[APIKey]: Paginated response containing list of API keys
        """
        params = {}
        if options:
            # Convert ListOptions to dict with correct parameter names
            if options.page_num > 0:
                params["page_num"] = str(options.page_num)
            else:
                params["page_num"] = "1"

            if options.page_size > 0:
                params["page_size"] = str(options.page_size)
            else:
                params["page_size"] = "10"
        else:
            # Set default values
            params["page_num"] = "1"
            params["page_size"] = "10"

        return self.client.get_paginated(
            endpoint=ENDPOINT_API_KEY_LIST,
            result_model=PaginatedResponse[APIKey],
            params=params,
        )
