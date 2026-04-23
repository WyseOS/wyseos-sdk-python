"""
Data models
"""

from datetime import datetime
from typing import Annotated, Any, Dict, Generic, List, Optional, TypeVar

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
        validate_by_name = True


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
        validate_by_name = True


class TeamParameters(BaseModel):
    """Parameters for team configuration (matches Go TeamParameterValue)."""

    system_prompt_role: str = Field(alias="system_prompt_role")
    system_prompt_task_skill: str = Field(alias="system_prompt_task_skill")
    max_turns: int = Field(alias="max_turns")
    temperature: float = Field(alias="temperature")

    class Config:
        validate_by_name = True


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
        validate_by_name = True


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
        validate_by_name = True


class Attachments(BaseModel):
    """Attachment model compatible with protocol SessionFileType/AttachmentType."""

    file_name: str = Field(default="", alias="file_name")
    file_url: str = Field(default="", alias="file_url")
    extension: Optional[str] = None
    url: Optional[str] = None
    attachment_id: Optional[str] = Field(default=None, alias="attachment_id")
    message_id: Optional[str] = Field(default=None, alias="message_id")
    file_type: Optional[str] = Field(default=None, alias="file_type")
    file_size: Optional[int] = Field(default=None, alias="file_size")
    created_at: Optional[str] = Field(default=None, alias="created_at")
    updated_at: Optional[str] = Field(default=None, alias="updated_at")

    class Config:
        validate_by_name = True


class UserTaskMessage(BaseModel):
    """User task message structure."""

    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Response message structure aligned with session protocol."""

    type: str = ""
    message_id: str = Field(default="", alias="message_id")
    source: str = ""
    source_component: str = Field(default="", alias="source_component")
    source_type: str = Field(default="", alias="source_type")
    content: str = ""
    created_at: str = Field(default="", alias="created_at")
    browser_id: Optional[str] = Field(default=None, alias="browser_id")
    session_round: Optional[int] = Field(default=None, alias="session_round")
    timestamp: Optional[int] = None
    attachments: List["Attachments"] = Field(default_factory=list)
    code: Optional[int] = None
    error: Optional[str] = None
    chunk_id: Optional[str] = Field(default=None, alias="chunk_id")
    chunk_index: Optional[int] = Field(default=None, alias="chunk_index")
    delta: Optional[bool] = None
    message: Any = None

    class Config:
        validate_by_name = True


class SessionInfo(BaseModel):
    """Information about a session aligned with session protocol."""

    session_id: str = Field(alias="session_id")
    name: str = ""
    status: str = ""
    browser_id: str = Field(default="", alias="browser_id")
    team_id: Optional[str] = Field(default=None, alias="team_id")
    intent_id: Optional[str] = Field(default=None, alias="intent_id")
    task: List[UserTaskMessage] = Field(default_factory=list)
    task_result: Optional[Dict[str, Any]] = Field(default=None, alias="task_result")
    attachments: List["Attachments"] = Field(default_factory=list)
    platform: str = ""
    mode: Optional[str] = None
    visibility: str = ""
    extra: Optional[Dict[str, Any]] = None
    created_at: str = Field(default="", alias="created_at")
    updated_at: str = Field(default="", alias="updated_at")

    class Config:
        validate_by_name = True


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
        validate_by_name = True


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
        validate_by_name = True


class APIKey(BaseModel):
    """API key information."""

    name: str
    api_key: str = Field(alias="api_key")
    created_at: datetime = Field(alias="created_at")
    last_used_at: datetime = Field(alias="last_used_at")

    class Config:
        validate_by_name = True


# Request/Response Types
class APIResponse(BaseModel, Generic[T]):
    """API response model."""

    code: int
    msg: str
    data: T


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model."""

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
    """Request to create a new session."""

    task: Annotated[str, Field(min_length=1)]
    intent_id: Optional[str] = None
    mode: Optional[str] = None
    platform: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""

    name: str


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


class OAuthURLResponse(BaseModel):
    """Response for retrieving an OAuth authorization URL."""

    auth_url: str


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

    role: Optional[str] = None
    content: Optional[str] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None


class UpdateSessionNameRequest(BaseModel):
    """Request to update session name."""

    session_id: str
    title: str


# Product models
class ProductAttachment(BaseModel):
    """Attachment payload used by product create API."""

    file_name: str = Field(alias="file_name")
    file_url: str = Field(alias="file_url")

    class Config:
        validate_by_name = True


class CreateProductRequest(BaseModel):
    """Request body for POST /dashboard/product/create."""

    product: str
    attachments: List[ProductAttachment] = Field(default_factory=list)


class CreateProductResponse(BaseModel):
    """Response body for POST /dashboard/product/create."""

    product_id: str = Field(alias="product_id")
    product_name: str = Field(alias="product_name", default="")
    status: str = ""

    class Config:
        validate_by_name = True


class AnalysisResult(BaseModel):
    """Nested analysis result from product info API."""

    report_id: Optional[str] = Field(alias="report_id", default=None)

    class Config:
        validate_by_name = True


class ProductInfo(BaseModel):
    """Response body for GET /dashboard/product/candidates/{product_id}/info."""

    product_id: str = Field(alias="product_id")
    product_name: str = Field(alias="product_name", default="")
    status: str = ""
    analysis_result: Optional[AnalysisResult] = Field(
        alias="analysis_result", default=None
    )
    description: Optional[str] = None
    has_guided: Optional[bool] = Field(alias="has_guided", default=None)

    class Config:
        validate_by_name = True


class Campaign(BaseModel):
    """Campaign item in product report."""

    name: str = ""
    description: str = ""


class IndustryLevel1(BaseModel):
    """Level1 industry item."""

    id: int = 0


class IndustryCondition(BaseModel):
    """Related industry condition in product report."""

    level1: Optional[IndustryLevel1] = None
    level2: Optional[List[int]] = None


class ProductReport(BaseModel):
    """Response body for GET /dashboard/report/info/{report_id}."""

    report_id: str = Field(alias="report_id", default="")
    product_name: str = Field(alias="product_name", default="")
    target_description: str = Field(alias="target_description", default="")
    keywords: List[str] = Field(default_factory=list)
    user_personas: List[str] = Field(alias="user_personas", default_factory=list)
    user_profiles: List[str] = Field(alias="user_profiles", default_factory=list)
    competitors: List[str] = Field(default_factory=list)
    recommended_campaigns: List[Campaign] = Field(
        alias="recommended_campaigns", default_factory=list
    )
    related_links: List[str] = Field(alias="related_links", default_factory=list)
    related_industries: Optional[List[IndustryCondition]] = Field(
        alias="related_industries", default=None
    )

    class Config:
        validate_by_name = True


class Category(BaseModel):
    """Industry category."""

    id: int = 0
    zh: str = ""
    en: str = ""
    en_desc: str = Field(alias="en_desc", default="")
    level: int = 0

    class Config:
        validate_by_name = True


class Industry(BaseModel):
    """Industry tree item from categories API."""

    category: Category
    subcategories: List[Category] = Field(default_factory=list)


# Marketing models
class TweetMedia(BaseModel):
    url: str = ""
    type: str = ""
    width: int = 0
    height: int = 0
    text_url: Optional[str] = None
    video_url: Optional[str] = None
    duration_ms: Optional[int] = None


class TweetWithReply(BaseModel):
    reply: str = ""
    tweet: str = ""
    tweet_id: str = Field(default="", alias="tweet_id")
    username: str = ""
    tweet_time: str = Field(default="", alias="tweet_time")
    url: str = ""
    bookmark_count: int = Field(default=0, alias="bookmark_count")
    favorite_count: int = Field(default=0, alias="favorite_count")
    quote_count: int = Field(default=0, alias="quote_count")
    reply_count: int = Field(default=0, alias="reply_count")
    retweet_count: int = Field(default=0, alias="retweet_count")
    view_count: int = Field(default=0, alias="view_count")
    user_profile: Optional[Dict[str, Any]] = Field(default=None, alias="user_profile")
    media: List[TweetMedia] = Field(default_factory=list)

    class Config:
        validate_by_name = True


class TweetInMessage(BaseModel):
    """TweetWithReply without reply field, used for like/retweet."""

    tweet: str = ""
    tweet_id: str = Field(default="", alias="tweet_id")
    username: str = ""
    tweet_time: str = Field(default="", alias="tweet_time")
    url: str = ""
    bookmark_count: int = Field(default=0, alias="bookmark_count")
    favorite_count: int = Field(default=0, alias="favorite_count")
    quote_count: int = Field(default=0, alias="quote_count")
    reply_count: int = Field(default=0, alias="reply_count")
    retweet_count: int = Field(default=0, alias="retweet_count")
    view_count: int = Field(default=0, alias="view_count")
    user_profile: Optional[Dict[str, Any]] = Field(default=None, alias="user_profile")
    media: List[TweetMedia] = Field(default_factory=list)

    class Config:
        validate_by_name = True


class TweetWriterData(BaseModel):
    draft_id: str = Field(default="", alias="draft_id")
    content: str = ""
    media: List[TweetMedia] = Field(default_factory=list)

    class Config:
        validate_by_name = True
