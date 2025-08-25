"""
Core API client for the WyseOS Python SDK.
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
    HEADER_ACCEPT,
    HEADER_API_KEY,
    HEADER_CONTENT_TYPE,
    HEADER_USER_AGENT,
)
from .errors import APIError
from .services.agent import AgentService
from .services.browser import BrowserService
from .services.session import SessionService
from .services.team import TeamService
from .services.user import UserService

T = TypeVar("T", bound=BaseModel)


class Client:
    """Main API client for the WyseOS."""

    def __init__(self, options: Optional[ClientOptions] = None):
        if options is None:
            options = ClientOptions()

        self.base_url = options.base_url or DEFAULT_BASE_URL
        self.api_key = options.api_key
        self.timeout = options.timeout or DEFAULT_TIMEOUT
        self.user_agent = "WyseOSPython/0.2.0"  # Set user_agent directly
        self.http_client = requests.Session()

        # Initialize services
        self.user = UserService(self)
        self.team = TeamService(self)
        self.agent = AgentService(self)
        self.session = SessionService(self)
        self.browser = BrowserService(self)

    def _do_request(
        self, method: str, endpoint: str, body: Optional[Dict] = None
    ) -> requests.Response:
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

            if response.status_code != 200:
                raise APIError(
                    message="Request failed", status_code=response.status_code
                )

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
        if params:
            endpoint = self._build_url(endpoint, params)

        response = self._do_request("GET", endpoint)
        response_data = response.json()

        if "code" in response_data and "data" in response_data:
            api_response = response_data
            if api_response.get("code") != 0:
                message = api_response.get("msg", "Unknown error")
                raise APIError(message=message, code=api_response.get("code"))

            data = api_response.get("data", {})
            return result_model.model_validate(data)
        else:
            return result_model.model_validate(response_data)

    def post(
        self,
        endpoint: str,
        body: Optional[Dict] = None,
        result_model: Optional[Type[T]] = None,
    ) -> Optional[T]:
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
        response = self._do_request("PUT", endpoint, body)
        if result_model and response.content:
            if result_model is dict:
                return response.json()
            return result_model.model_validate(response.json())
        return None

    def delete(self, endpoint: str) -> None:
        self._do_request("DELETE", endpoint)

    def _build_url(self, endpoint: str, params: Dict[str, str]) -> str:
        if not params:
            return endpoint

        query_string = urlencode(params)
        separator = "&" if "?" in endpoint else "?"

        return f"{endpoint}{separator}{query_string}"
