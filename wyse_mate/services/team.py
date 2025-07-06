"""
Team service for the Mate SDK Python.

This module contains the TeamService class for team-related API operations.
"""

from typing import TYPE_CHECKING, Optional

from ..constants import (
    ENDPOINT_TEAM_INFO,
    ENDPOINT_TEAM_LIST,
    TEAM_QUERY_TYPE_ALL,
)
from ..models import (
    APIResponse,
    ListOptions,
    PaginatedResponse,
    TeamInfo,
)

if TYPE_CHECKING:
    from ..client import Client


class TeamService:
    """
    Service for team-related API operations.

    This service provides methods for retrieving team information.
    """

    def __init__(self, client: "Client"):
        """
        Initialize the team service.

        Args:
            client: The main API client instance
        """
        self.client = client

    def get_list(
        self, team_type: str = "", options: Optional[ListOptions] = None
    ) -> PaginatedResponse[TeamInfo]:
        """
        Get a list of teams.

        Args:
            team_type: Type of teams to filter by (default: "all")
            options: Optional pagination options

        Returns:
            PaginatedResponse[TeamInfo]: Paginated response containing list of teams
        """
        params = {}
        if team_type:
            params["team_type"] = team_type
        else:
            params["team_type"] = TEAM_QUERY_TYPE_ALL

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
            endpoint=ENDPOINT_TEAM_LIST,
            result_model=PaginatedResponse[TeamInfo],
            params=params,
        )

    def get_info(self, team_id: str) -> TeamInfo:
        """
        Get information about a specific team.

        Args:
            team_id: ID of the team

        Returns:
            TeamInfo: Team information
        """
        endpoint = ENDPOINT_TEAM_INFO.format(team_id=team_id)
        resp = self.client.get(endpoint=endpoint, result_model=APIResponse[TeamInfo])
        return resp.data
