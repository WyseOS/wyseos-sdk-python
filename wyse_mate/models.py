"""
Data models for the Wyse Mate Python SDK.

This module contains Pydantic models for all data structures, requests, and responses
used in the Wyse Mate.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# Core Data Types
class ModelInfo(BaseModel):
    """Information about an AI model."""

    system_model_id: str = Field(alias="system_model_id")
    provider: str
    model_type: str = Field(alias="model_type")
    icon_url: str = Field(alias="icon_url")
    created_at: str = Field(alias="created_at")
    updated_at: str = Field(alias="updated_at")

    class Config:
        allow_population_by_field_name = True


class TeamType(str):
    """Team type enumeration."""

    PERSONAL = "personal"
    SHARED = "shared"


class AgentParameters(BaseModel):
    """Parameters for agent configuration (matches Go AgentParameterValue)."""

    system_prompt_role: str = Field(alias="system_prompt_role")
    system_prompt_task_skill: str = Field(alias="system_prompt_task_skill")
    temperature: float = Field(alias="temperature")

    class Config:
        allow_population_by_field_name = True


class TeamParameters(BaseModel):
    """Parameters for team configuration (matches Go TeamParameterValue)."""

    system_prompt_role: str = Field(alias="system_prompt_role")
    system_prompt_task_skill: str = Field(alias="system_prompt_task_skill")
    max_turns: int = Field(alias="max_turns")
    temperature: float = Field(alias="temperature")

    class Config:
        allow_population_by_field_name = True


class AgentInfo(BaseModel):
    """Information about an agent (matches Go AgentInfoResponse)."""

    agent_id: str = Field(alias="agent_id")
    user_id: str = Field(alias="user_id")
    avatar: str = Field(alias="avatar")
    name: str
    description: str
    system_message: str = Field(alias="system_message")
    component_type: str = Field(alias="component_type")
    model: ModelInfo
    agent_type: str = Field(alias="agent_type")
    parameters: AgentParameters
    created_at: datetime = Field(alias="created_at")
    updated_at: datetime = Field(alias="updated_at")

    class Config:
        allow_population_by_field_name = True


class TeamInfo(BaseModel):
    """Information about a team (matches Go MateTeamWithAgents)."""

    team_id: str = Field(alias="team_id")
    user_id: str = Field(alias="user_id")
    avatar: str = Field(alias="avatar")
    name: str
    description: str
    component_type: str = Field(alias="component_type")
    team_type: str = Field(alias="team_type")
    agents: List[AgentInfo] = Field(default_factory=list)
    termination: str = Field(alias="termination")
    model: ModelInfo
    parameters: TeamParameters
    created_at: datetime = Field(alias="created_at")
    updated_at: datetime = Field(alias="updated_at")
    deleted_at: int = Field(alias="deleted_at")

    class Config:
        allow_population_by_field_name = True


class Attachments(BaseModel):
    """File attachments for messages."""

    attachment_id: str = Field(alias="attachment_id")
    message_id: str = Field(alias="message_id")
    file_name: str = Field(alias="file_name")
    file_type: str = Field(alias="file_type")
    extension: str
    file_size: int = Field(alias="file_size")
    file_url: str = Field(alias="file_url")
    created_at: str = Field(alias="created_at")
    updated_at: str = Field(alias="updated_at")

    class Config:
        allow_population_by_field_name = True


class UserTaskMessage(BaseModel):
    """User task message structure."""

    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Response message structure (matches Go MessageResponse)."""

    message_id: str = Field(alias="message_id")
    source: str
    source_type: str = Field(alias="source_type")
    source_component: str = Field(alias="source_component")
    content: str
    message: Any = Field(alias="message")
    type: str = Field(alias="type")
    created_at: str = Field(alias="created_at")
    attachments: List["Attachments"] = Field(default_factory=list)
    session_round: int = Field(alias="session_round")

    class Config:
        allow_population_by_field_name = True


class SessionInfo(BaseModel):
    """Information about a session (matches Go SessionInfoResponse)."""

    session_id: str = Field(alias="session_id")
    status: str
    browser_id: str = Field(alias="browser_id")
    team_id: str = Field(alias="team_id")
    intent_id: str = Field(alias="intent_id")
    name: str
    task: List[UserTaskMessage] = Field(alias="task")
    task_result: Dict[str, Any] = Field(alias="task_result")
    messages: List[MessageResponse] = Field(default_factory=list)
    duration: int
    error_message: str = Field(alias="error_message")
    attachments: List["Attachments"] = Field(default_factory=list)
    platform: str
    visibility: str
    created_at: str = Field(alias="created_at")
    updated_at: str = Field(alias="updated_at")

    class Config:
        allow_population_by_field_name = True


class BrowserPageInfo(BaseModel):
    """Information about a browser page (matches Go BrowserPageInfoResponse)."""

    index: int
    url: str
    status: str
    video_url: str = Field(alias="video_url")
    ws_debugger_url: str = Field(alias="ws_debugger_url")
    front_debugger_url: str = Field(alias="front_debugger_url")
    page_id: str = Field(alias="page_id")
    debugger_host: str = Field(alias="debugger_host")

    class Config:
        allow_population_by_field_name = True


class BrowserInfo(BaseModel):
    """Information about a browser instance (matches Go BrowserInfoResponse)."""

    browser_id: str = Field(alias="browser_id")
    user_id: str = Field(alias="user_id")
    session_id: str = Field(alias="session_id")
    status: str
    width: int
    height: int
    ws_endpoint: str = Field(alias="ws_endpoint")
    solve_captcha: bool = Field(alias="solve_captcha")
    timezone: str
    user_agent: str = Field(alias="user_agent")
    duration_seconds: int = Field(alias="duration_seconds")
    created_at: str = Field(alias="created_at")
    pages: List[BrowserPageInfo] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True


class APIKey(BaseModel):
    """API key information."""

    id: int = Field(alias="id")
    name: str
    api_key: str = Field(alias="api_key")
    created_at: datetime = Field(alias="created_at")
    last_used_at: datetime = Field(alias="last_used_at")

    class Config:
        allow_population_by_field_name = True


# Request/Response Types
class APIResponse(BaseModel, Generic[T]):
    """通用API响应模型，适用于{code, msg, data}结构。"""

    code: int
    msg: str
    data: T


class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应模型，适用于所有分页列表接口。"""

    page_num: int
    page_size: int
    total: int
    total_page: int
    data: List[T]


class ListOptions(BaseModel):
    """Options for list operations."""

    page_num: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# Specific Request Types
class CreateTeamRequest(BaseModel):
    """Request to create a new team."""

    name: str
    description: Optional[str] = None
    team_type: str
    model: ModelInfo
    parameters: Optional[TeamParameters] = None


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""

    name: str
    description: Optional[str] = None
    team_id: Optional[str] = Field(default=None, alias="team_id")
    model: ModelInfo
    parameters: Optional[AgentParameters] = None
    system_prompt: Optional[str] = Field(default=None, alias="system_prompt")


class CreateSessionRequest(BaseModel):
    """Request to create a new session (matches Go API)."""

    team_id: str = Field(alias="team_id")
    task: Optional[str] = Field(default="", description="The task for the session")


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""

    name: str
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = Field(default=None, alias="expires_at")


# Specific Response Types
class CreateTeamResponse(BaseModel):
    """Response for creating a team."""

    team: TeamInfo


class CreateAgentResponse(BaseModel):
    """Response for creating an agent."""

    agent: AgentInfo


class CreateSessionResponse(BaseModel):
    """Response for creating a session (matches Go API)."""

    session_id: str = Field(alias="session_id")


class CreateAPIKeyResponse(BaseModel):
    """Response for creating an API key."""

    api_key: APIKey
    key_value: str = Field(
        alias="key_value"
    )  # Full key value returned only on creation


class ListBrowsersResponse(BaseModel):
    """Response for listing browsers."""

    browsers: List[BrowserInfo]
    total: int


class ListBrowserPagesResponse(BaseModel):
    """Response for listing browser pages."""

    pages: List[BrowserPageInfo]
    total: int


class GetMessagesResponse(BaseModel):
    """Response for getting session messages."""

    messages: List[MessageResponse]
    total_count: int
    has_next: bool = Field(default=False)
    has_prev: bool = Field(default=False)


class MessageFilter(BaseModel):
    """Filter for session messages."""

    role: Optional[str] = None  # "user", "assistant", "system"
    content: Optional[str] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None


class UpdateSessionNameRequest(BaseModel):
    """Request to update session name."""

    session_id: str
    title: str
