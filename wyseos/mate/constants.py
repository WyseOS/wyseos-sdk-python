"""
Constants

This module contains all constants used throughout the SDK.
"""

# Default configuration file
DEFAULT_CONFIG_FILE = "mate.yaml"

# Default Configuration
DEFAULT_BASE_URL = "https://api.wyseos.com"
DEFAULT_TIMEOUT = 30  # seconds

# HTTP Headers
HEADER_API_KEY = "x-api-key"
HEADER_AUTHORIZATION = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_USER_AGENT = "User-Agent"
HEADER_ACCEPT = "Accept"
HEADER_REQUEST_ID = "X-Request-ID"

# Content Types
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"
CONTENT_TYPE_MULTIPART = "multipart/form-data"

# API Endpoints
# User endpoints
ENDPOINT_API_KEY_LIST = "/user/apikey/lists"
ENDPOINT_AUTH_URL = "/auth/url"
ENDPOINT_AUTH_EMAIL_LINK_SIGNINUP = "/auth/otp/signinup"

# X (Twitter) connector endpoints
ENDPOINT_X_CONNECTOR_ACCOUNTS = "/connectors/v1/x/accounts"
ENDPOINT_X_CONNECTOR_AUTHORIZE = "/connectors/v1/x/accounts/authorize"
ENDPOINT_X_CONNECTOR_DELETE = "/connectors/v1/x/accounts/{connector_id}"

# Team endpoints
ENDPOINT_TEAM_LIST = "/team/lists"
ENDPOINT_TEAM_INFO = "/team/info/{team_id}"

# Agent endpoints
ENDPOINT_AGENT_LIST = "/agent/lists"
ENDPOINT_AGENT_INFO = "/agent/info/{agent_id}"

# Session endpoints
ENDPOINT_SESSION_CREATE = "/session/create"
ENDPOINT_SESSION_INFO = "/session/info/{session_id}"
ENDPOINT_SESSION_LIST = "/session/lists"
ENDPOINT_SESSION_MESSAGES = "/session/message/lists"
ENDPOINT_SESSION_MESSAGES_BETWEEN = "/session/message/between"
ENDPOINT_SESSION_WEBSOCKET = "/session/ws/{session_id}"
ENDPOINT_SESSION_STOP = "/session/stop/{session_id}"

# Marketing endpoints
ENDPOINT_SESSION_MARKETING_DATA = "/session/marketing/data/{session_id}"
ENDPOINT_MARKETING_PRODUCT_INFO = "/dashboard/product/candidates/{product_id}/info"
ENDPOINT_MARKETING_REPORT_INFO = "/dashboard/report/info/{report_id}"
ENDPOINT_MARKETING_REPORT_UPDATE = "/dashboard/report/update/{report_id}"
ENDPOINT_MARKETING_RESEARCH_TWEETS = "/dashboard/product/query/results/{query_id}/lists"

# Product endpoints
ENDPOINT_PRODUCT_CREATE = "/dashboard/product/create"
ENDPOINT_PRODUCT_CATEGORIES = "/dashboard/categories"

# Product status
PRODUCT_STATUS_PENDING = "pending"
PRODUCT_STATUS_COMPLETED = "completed"

# Product polling defaults
PRODUCT_POLL_INTERVAL = 20  # seconds
PRODUCT_POLL_MAX_ATTEMPTS = 30  # default 10 minutes timeout

# Browser endpoints
ENDPOINT_BROWSER_INFO = "/browser/info/{browser_id}"
ENDPOINT_BROWSER_LIST = "/browser/lists"
ENDPOINT_BROWSER_RELEASE = "/browser/release/{browser_id}"
ENDPOINT_BROWSER_PAGE_LIST = "/browser/page/lists"

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1
DEFAULT_PAGE_NUM = 1

# Timeouts
DEFAULT_CONNECT_TIMEOUT = 5  # seconds
DEFAULT_READ_TIMEOUT = 30  # seconds
DEFAULT_WEBSOCKET_TIMEOUT = 60  # seconds

# WebSocket
WEBSOCKET_PROTOCOL = "wss"
WEBSOCKET_HEARTBEAT_INTERVAL = 30  # seconds
WEBSOCKET_MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB

# Team types
TEAM_TYPE_DEEP_RESEARCH = "deep_research"
TEAM_TYPE_WYSE_MATE = "wyse_mate"

# Agent types
AGENT_TYPE_BROWSER = "wyse_browser"
AGENT_TYPE_FILE_READER = "file_analyst"
AGENT_TYPE_CODER = "coder"
AGENT_TYPE_SEARCH = "search"
AGENT_TYPE_ARTIST = "artist"
AGENT_TYPE_ASSISTANT = "assistant"
AGENT_TYPE_GUARDIAN = "guardian"
AGENT_TYPE_USER_PROXY = "user_proxy"
AGENT_TYPE_SUMMARY = "summary"

# Session status
SESSION_STATUS_CREATED = "created"
SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_COMPLETE = "complete"
SESSION_STATUS_PAUSED = "paused"
SESSION_STATUS_STOPPED = "stopped"
SESSION_STATUS_ERROR = "error"

# Platform
PLATFORM_EXTENSION = "extension"
PLATFORM_API = "api"
PLATFORM_WEB = "web"

# Mode
MODE_MARKETING = "marketing"

# Rich message sub-types
RICH_TYPE_MARKETING_TWEET_REPLY = "marketing_tweet_reply"
RICH_TYPE_MARKETING_TWEET_INTERACT = "marketing_tweet_interact"
RICH_TYPE_WRITER_TWITTER = "writer_twitter"
RICH_TYPE_MARKETING_REPORT = "marketing_report"
RICH_TYPE_MARKETING_RESEARCH_TWEETS = "marketing_research_tweets"
RICH_TYPE_FOLLOW_UP_SUGGESTION = "follow_up_suggestion"
RICH_TYPE_X_BROWSER_ACTION = "x_browser_action"
RICH_TYPE_SKILL = "skill"

# Browser status
BROWSER_STATUS_CREATED = "created"
BROWSER_STATUS_ACTIVE = "active"
BROWSER_STATUS_ERROR = "error"
BROWSER_STATUS_RELEASING = "releasing"
BROWSER_STATUS_RELEASED = "released"

# Agent Query Types (for listing agents)
AGENT_QUERY_TYPE_ALL = "all"
AGENT_QUERY_TYPE_SYSTEM = "system"
AGENT_QUERY_TYPE_USER = "user"

# Team Query Types (for listing teams)
TEAM_QUERY_TYPE_ALL = "all"
TEAM_QUERY_TYPE_SYSTEM = "system"
TEAM_QUERY_TYPE_USER = "user"
