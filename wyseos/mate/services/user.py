"""
User service for the WyseOS SDK Python.
"""

from typing import TYPE_CHECKING, Optional

from ..constants import (
    ENDPOINT_API_KEY_LIST,
    ENDPOINT_AUTH_URL,
)
from ..extension_host import resolve_extension_webapp_host
from ..models import (
    APIKey,
    APIResponse,
    ListOptions,
    OAuthURLResponse,
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

    def get_x_oauth_url(self) -> OAuthURLResponse:
        """
        Get an OAuth authorization URL for Twitter login.

        Returns:
            OAuthURLResponse: Response containing the OAuth authorization URL
        """
        params = {
            "type": "login",
            "platform": "twitter",
            "credential_type": "api_key",
            "redirect_url": f"{resolve_extension_webapp_host()}/oauth/twitter",
        }

        resp = self.client.get(
            endpoint=ENDPOINT_AUTH_URL,
            result_model=APIResponse[OAuthURLResponse],
            params=params,
        )
        return resp.data
