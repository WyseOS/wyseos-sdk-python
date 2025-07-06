"""
Session service for the Mate SDK Python.

This module contains the SessionService class for session-related API operations.
"""

from typing import TYPE_CHECKING, Optional

from ..constants import (
    ENDPOINT_SESSION_CREATE,
    ENDPOINT_SESSION_INFO,
    ENDPOINT_SESSION_MESSAGES,
    ENDPOINT_SESSION_MESSAGES_BETWEEN,
)
from ..models import (
    APIResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    GetMessagesResponse,
    MessageFilter,
    MessageResponse,
    SessionInfo,
    UpdateSessionNameRequest,
)

if TYPE_CHECKING:
    from ..client import Client


class SessionService:
    """
    Service for session-related API operations.

    This service provides methods for managing sessions and session messages.
    """

    def __init__(self, client: "Client"):
        """
        Initialize the session service.

        Args:
            client: The main API client instance
        """
        self.client = client

    def create(self, request: CreateSessionRequest) -> CreateSessionResponse:
        """
        Create a new session.

        Args:
            request: Session creation request

        Returns:
            CreateSessionResponse: Response containing the created session
        """
        resp = self.client.post(
            endpoint=ENDPOINT_SESSION_CREATE,
            body=request.dict(exclude_none=True),
            result_model=dict,
        )
        print(ENDPOINT_SESSION_CREATE)
        print(resp)
        if resp.get("code") != 0:
            from ..errors import APIError

            raise APIError(
                message=resp.get("msg", "Unknown error"), code=resp.get("code")
            )
        return CreateSessionResponse(**resp["data"])

    def get_info(self, session_id: str) -> SessionInfo:
        """
        Get information about a specific session.

        Args:
            session_id: ID of the session

        Returns:
            SessionInfo: Session information
        """
        endpoint = ENDPOINT_SESSION_INFO.format(session_id=session_id)
        resp = self.client.get(endpoint=endpoint, result_model=APIResponse[SessionInfo])
        return resp.data

    def get_messages(
        self,
        session_id: str,
        page_num: int = 1,
        page_size: int = 20,
        filter: Optional[MessageFilter] = None,
    ) -> GetMessagesResponse:
        """
        Get messages for a specific session.

        Args:
            session_id: ID of the session
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20)
            filter: Optional message filter

        Returns:
            GetMessagesResponse: Response containing session messages
        """
        params = {
            "session_id": session_id,
            "page_num": str(page_num),
            "page_size": str(page_size),
        }
        if filter:
            params.update(filter.model_dump(exclude_none=True))
        resp = self.client.get(
            endpoint=ENDPOINT_SESSION_MESSAGES,
            result_model=dict,
            params=params,
        )

        if resp.get("code") != 0:
            from ..errors import APIError

            raise APIError(
                message=resp.get("msg", "Unknown error"), code=resp.get("code")
            )

        pagination_data = resp.get("data", {})
        messages_raw = pagination_data.get("data", [])
        messages_list = [MessageResponse.model_validate(msg) for msg in messages_raw]
        total_count = pagination_data.get("total", 0)
        current_page_num = pagination_data.get("page_num", 1)
        current_page_size = pagination_data.get("page_size", 20)
        total_pages = pagination_data.get("total_page", 0)
        has_next = current_page_num * current_page_size < total_count
        has_prev = current_page_num > 1

        return GetMessagesResponse(
            messages=messages_list,
            total_count=total_count,
            has_next=has_next,
            has_prev=has_prev,
        )

    def get_between_messages(
        self, session_id: str, from_message_id: str, to_message_id: str
    ) -> GetMessagesResponse:
        """
        Get messages between two specific message IDs.

        Args:
            session_id: ID of the session
            from_message_id: Starting message ID
            to_message_id: Ending message ID

        Returns:
            GetMessagesResponse: Response containing messages between the specified IDs
        """
        params = {
            "session_id": session_id,
            "from_message_id": from_message_id,
            "to_message_id": to_message_id,
        }

        resp = self.client.get(
            endpoint=ENDPOINT_SESSION_MESSAGES_BETWEEN,
            result_model=dict,
            params=params,
        )

        if resp.get("code") != 0:
            from ..errors import APIError

            raise APIError(
                message=resp.get("msg", "Unknown error"), code=resp.get("code")
            )

        # For get_between_messages, the data is a direct list of messages
        messages_raw = resp.get("data", [])
        messages_list = [MessageResponse.model_validate(msg) for msg in messages_raw]

        # Since this endpoint doesn't return pagination info, set defaults
        total_count = len(messages_list)
        has_next = False
        has_prev = False

        return GetMessagesResponse(
            messages=messages_list,
            total_count=total_count,
            has_next=has_next,
            has_prev=has_prev,
        )

    def update_session_name(self, request: UpdateSessionNameRequest) -> None:
        """
        Update the name of a session.

        Args:
            request: Session name update request
        """
        endpoint = ENDPOINT_SESSION_INFO.format(session_id=request.session_id)
        self.client.put(endpoint=endpoint, body=request.dict(exclude_none=True))
