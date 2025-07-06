"""
Agent service for the Mate SDK Python.

This module contains the AgentService class for agent-related API operations.
"""

from typing import TYPE_CHECKING, Optional

from ..constants import (
    AGENT_QUERY_TYPE_ALL,
    ENDPOINT_AGENT_INFO,
    ENDPOINT_AGENT_LIST,
)
from ..models import (
    AgentInfo,
    APIResponse,
    ListOptions,
    PaginatedResponse,
)

if TYPE_CHECKING:
    from ..client import Client


class AgentService:
    """
    Service for agent-related API operations.

    This service provides methods for retrieving agent information.
    """

    def __init__(self, client: "Client"):
        """
        Initialize the agent service.

        Args:
            client: The main API client instance
        """
        self.client = client

    def get_list(
        self, agent_type: str = "", options: Optional[ListOptions] = None
    ) -> PaginatedResponse[AgentInfo]:
        """
        Get a list of agents.

        Args:
            agent_type: Type of agents to filter by (default: "all")
            options: Optional pagination options

        Returns:
            PaginatedResponse[AgentInfo]: Paginated response containing list of agents
        """
        params = {}
        if agent_type:
            params["agent_type"] = agent_type
        else:
            params["agent_type"] = AGENT_QUERY_TYPE_ALL

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
            endpoint=ENDPOINT_AGENT_LIST,
            result_model=PaginatedResponse[AgentInfo],
            params=params,
        )

    def get_info(self, agent_id: str) -> AgentInfo:
        """
        Get information about a specific agent.

        Args:
            agent_id: ID of the agent

        Returns:
            AgentInfo: Agent information
        """
        endpoint = ENDPOINT_AGENT_INFO.format(agent_id=agent_id)
        resp = self.client.get(endpoint=endpoint, result_model=APIResponse[AgentInfo])
        return resp.data
