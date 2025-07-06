"""
Core API client for the Wyse Mate Python SDK.

This module contains the main Client class responsible for handling HTTP requests
and overall API communication.
"""

from typing import Dict, Optional, Type, TypeVar
from urllib.parse import urlencode, urljoin

import requests
from pydantic import BaseModel

from .config import ClientOptions
from .constants import (
    CONTENT_TYPE_JSON,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    HEADER_ACCEPT,
    HEADER_API_KEY,
    HEADER_CONTENT_TYPE,
    HEADER_USER_AGENT,
)
from .errors import _handle_api_error
from .services.agent import AgentService
from .services.browser import BrowserService
from .services.session import SessionService
from .services.team import TeamService
from .services.user import UserService

T = TypeVar("T", bound=BaseModel)


class Client:
    """
    Main API client for the Wyse Mate.

    This class provides methods for making HTTP requests to the Wyse Mate
    and manages all service instances.
    """

    def __init__(self, options: Optional[ClientOptions] = None):
        """
        Initialize the Wyse Mate client.

        Args:
            options: Client configuration options. If None, uses default values.
        """
        if options is None:
            options = ClientOptions()

        self.base_url = options.base_url or DEFAULT_BASE_URL
        self.api_key = options.api_key
        self.timeout = options.timeout or DEFAULT_TIMEOUT
        self.user_agent = options.user_agent or DEFAULT_USER_AGENT
        self.http_client = options.http_client or requests.Session()

        # Initialize services
        self.user = UserService(self)
        self.team = TeamService(self)
        self.agent = AgentService(self)
        self.session = SessionService(self)
        self.browser = BrowserService(self)

    def _do_request(
        self, method: str, endpoint: str, body: Optional[Dict] = None
    ) -> requests.Response:
        """
        Internal method to perform HTTP requests.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            body: Request body data (will be JSON serialized)

        Returns:
            requests.Response: HTTP response object

        Raises:
            APIError: If the API returns an error response
            NetworkError: If there's a network-related issue
        """
        url = urljoin(self.base_url, endpoint)

        headers = {
            HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
            HEADER_USER_AGENT: self.user_agent,
            HEADER_ACCEPT: CONTENT_TYPE_JSON,
        }

        if self.api_key:
            headers[HEADER_API_KEY] = self.api_key

        try:
            response = self.http_client.request(
                method=method, url=url, headers=headers, json=body, timeout=self.timeout
            )

            # Handle API errors
            if response.status_code >= 400:
                _handle_api_error(response)

            return response

        except requests.exceptions.RequestException as e:
            from .errors import NetworkError

            raise NetworkError(
                f"Network error during {method} request to {url}: {str(e)}", cause=e
            )

    def get(
        self,
        endpoint: str,
        result_model: Type[T],
        params: Optional[Dict[str, str]] = None,
    ) -> T:
        """
        Perform a GET request.

        Args:
            endpoint: API endpoint path
            result_model: Pydantic model class to deserialize response into
            params: Optional query parameters

        Returns:
            Instance of result_model with deserialized response data
        """
        if params:
            endpoint = self._build_url(endpoint, params)
        response = self._do_request("GET", endpoint)
        if result_model is dict:
            return response.json()
        return result_model.model_validate(response.json())

    def get_paginated(
        self,
        endpoint: str,
        result_model: Type[T],
        params: Optional[Dict[str, str]] = None,
    ) -> T:
        """
        Perform a GET request for paginated API responses.

        Args:
            endpoint: API endpoint path
            result_model: Pydantic model class to deserialize response into
            params: Optional query parameters

        Returns:
            Instance of result_model with deserialized response data
        """
        if params:
            endpoint = self._build_url(endpoint, params)

        response = self._do_request("GET", endpoint)

        # Parse the nested API response structure
        response_data = response.json()

        # Check if the response has the expected structure
        if "code" in response_data and "data" in response_data:
            # This is a nested API response
            api_response = response_data
            if api_response.get("code") != 0:
                # Handle API error
                message = api_response.get("msg", "Unknown error")
                from .errors import APIError

                raise APIError(message=message, code=api_response.get("code"))

            # Extract the actual data
            data = api_response.get("data", {})
            return result_model.model_validate(data)
        else:
            # Direct response structure
            return result_model.model_validate(response_data)

    def post(
        self,
        endpoint: str,
        body: Optional[Dict] = None,
        result_model: Optional[Type[T]] = None,
    ) -> Optional[T]:
        """
        Perform a POST request.

        Args:
            endpoint: API endpoint path
            body: Request body data
            result_model: Optional Pydantic model class to deserialize response into

        Returns:
            Instance of result_model if provided, None otherwise
        """
        response = self._do_request("POST", endpoint, body)
        if result_model and response.content:
            if result_model is dict:
                return response.json()
            return result_model.model_validate(response.json())
        return None

    def put(
        self,
        endpoint: str,
        body: Optional[Dict] = None,
        result_model: Optional[Type[T]] = None,
    ) -> Optional[T]:
        """
        Perform a PUT request.

        Args:
            endpoint: API endpoint path
            body: Request body data
            result_model: Optional Pydantic model class to deserialize response into

        Returns:
            Instance of result_model if provided, None otherwise
        """
        response = self._do_request("PUT", endpoint, body)
        if result_model and response.content:
            if result_model is dict:
                return response.json()
            return result_model.model_validate(response.json())
        return None

    def delete(self, endpoint: str) -> None:
        """
        Perform a DELETE request.

        Args:
            endpoint: API endpoint path
        """
        self._do_request("DELETE", endpoint)

    def _build_url(self, endpoint: str, params: Dict[str, str]) -> str:
        """
        Construct a URL with query parameters.

        Args:
            endpoint: Base endpoint path
            params: Query parameters

        Returns:
            URL with encoded query parameters
        """
        if not params:
            return endpoint

        query_string = urlencode(params)
        separator = "&" if "?" in endpoint else "?"

        return f"{endpoint}{separator}{query_string}"
