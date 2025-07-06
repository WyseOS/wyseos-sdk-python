"""
Browser service for the Mate SDK Python.

This module contains the BrowserService class for browser-related API operations.
"""

from typing import TYPE_CHECKING, Optional

from ..constants import (
    ENDPOINT_BROWSER_INFO,
    ENDPOINT_BROWSER_LIST,
    ENDPOINT_BROWSER_PAGE_LIST,
    ENDPOINT_BROWSER_RELEASE,
)
from ..models import (
    BrowserInfo,
    ListBrowserPagesResponse,
    ListBrowsersResponse,
    ListOptions,
)

if TYPE_CHECKING:
    from ..client import Client


class BrowserService:
    """
    Service for browser-related API operations.

    This service provides methods for managing browsers and browser pages.
    """

    def __init__(self, client: "Client"):
        """
        Initialize the browser service.

        Args:
            client: The main API client instance
        """
        self.client = client

    def get_info(self, browser_id: str) -> BrowserInfo:
        """
        Get information about a specific browser.

        Args:
            browser_id: ID of the browser

        Returns:
            BrowserInfo: Browser information
        """
        endpoint = ENDPOINT_BROWSER_INFO.format(browser_id=browser_id)
        return self.client.get(endpoint=endpoint, result_model=BrowserInfo)

    def list_browsers(
        self, session_id: str, options: Optional[ListOptions] = None
    ) -> ListBrowsersResponse:
        """
        List all browsers.

        Args:
            session_id: ID of the session to filter browsers by.
            options: Optional pagination options

        Returns:
            ListBrowsersResponse: Response containing list of browsers
        """
        params = {"session_id": session_id}
        if options:
            params.update(options.dict(exclude_none=True))

        resp = self.client.get(
            endpoint=ENDPOINT_BROWSER_LIST,
            result_model=dict,  # Get the raw dict response
            params=params,
        )

        if resp.get("code") != 0:
            from ..errors import APIError

            raise APIError(
                message=resp.get("msg", "Unknown error"), code=resp.get("code")
            )

        # Extract the actual data from the nested 'data' field
        browsers_data = resp.get("data", {})

        return ListBrowsersResponse.model_validate(browsers_data)

    def release_browser(self, browser_id: str) -> None:
        """
        Release a browser instance.

        Args:
            browser_id: ID of the browser to release
        """
        endpoint = ENDPOINT_BROWSER_RELEASE.format(browser_id=browser_id)
        self.client.delete(endpoint=endpoint)

    def list_browser_pages(
        self, browser_id: str, options: Optional[ListOptions] = None
    ) -> ListBrowserPagesResponse:
        """
        List all pages for a browser.

        Args:
            browser_id: ID of the browser
            options: Optional pagination options

        Returns:
            ListBrowserPagesResponse: Response containing list of browser pages
        """
        params = {"browser_id": browser_id}
        if options:
            params.update(options.dict(exclude_none=True))

        return self.client.get(
            endpoint=ENDPOINT_BROWSER_PAGE_LIST,
            result_model=ListBrowserPagesResponse,
            params=params,
        )
