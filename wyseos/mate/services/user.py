"""
User service for the WyseOS SDK Python.
"""

from typing import TYPE_CHECKING, Optional

from ..constants import (
    ENDPOINT_API_KEY_LIST,
    ENDPOINT_AUTH_EMAIL_LINK_SIGNINUP,
    ENDPOINT_AUTH_URL,
    ENDPOINT_X_CONNECTOR_ACCOUNTS,
    ENDPOINT_X_CONNECTOR_AUTHORIZE,
    ENDPOINT_X_CONNECTOR_DELETE,
)
from ..extension_host import resolve_extension_webapp_host
from ..models import (
    APIKey,
    APIResponse,
    AuthorizeXAccountRequest,
    ListOptions,
    ListXAccountsResponse,
    OAuthURLResponse,
    EmailLinkVerifyRequest,
    EmailLinkVerifyResponse,
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

    def start_email_verification(
        self, email: str, invite_code: Optional[str] = None
    ) -> EmailLinkVerifyResponse:
        """
        Start email magic-link sign in / sign up (link sent to the given address).

        Args:
            email: The email address to send the sign-in link to
            invite_code: Optional invite code

        Returns:
            EmailLinkVerifyResponse: Contains sign_type and pre_auth_id for completing
                verification after the user follows the link.
        """
        payload = EmailLinkVerifyRequest(email=email, invite_code=invite_code)

        resp = self.client.post(
            endpoint=ENDPOINT_AUTH_EMAIL_LINK_SIGNINUP,
            body=payload.model_dump(exclude_none=True),
            result_model=APIResponse[EmailLinkVerifyResponse],
            skip_auth=True,
        )
        return resp.data

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
            skip_auth=True,
        )
        return resp.data

    def list_x_accounts(self) -> ListXAccountsResponse:
        """
        List the current user's connected X (Twitter) accounts.

        Returns:
            ListXAccountsResponse: Response containing the list of X connector accounts
        """
        resp = self.client.get(
            endpoint=ENDPOINT_X_CONNECTOR_ACCOUNTS,
            result_model=APIResponse[ListXAccountsResponse],
        )
        return resp.data

    def authorize_x_account(
        self, target_connector_id: Optional[str] = None
    ) -> OAuthURLResponse:
        """
        Start the OAuth authorization flow to bind an X (Twitter) account.

        Args:
            target_connector_id: Optional ID of the credential slot to bind the X
                account to. When omitted, the backend creates a new credential.

        Returns:
            OAuthURLResponse: Response containing the authorization URL
        """
        payload = AuthorizeXAccountRequest(
            target_credential_id=target_connector_id,
            redirect_url=(
                f"{resolve_extension_webapp_host()}"
                "/settings/integrations/x/callback?scene=connector_x_bind"
            ),
        )

        resp = self.client.post(
            endpoint=ENDPOINT_X_CONNECTOR_AUTHORIZE,
            body=payload.model_dump(exclude_none=True),
            result_model=APIResponse[OAuthURLResponse],
        )
        return resp.data

    def delete_x_account(self, connector_id: str) -> None:
        """
        Delete a connected X (Twitter) account.

        Args:
            connector_id: ID of the X connector account to delete
        """
        endpoint = ENDPOINT_X_CONNECTOR_DELETE.format(connector_id=connector_id)
        self.client.delete(endpoint)
