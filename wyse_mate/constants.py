"""
Constants for the Wyse Mate Python SDK.

This module contains all constants used throughout the SDK.
"""

# Default Configuration
DEFAULT_BASE_URL = "https://api.mate.wyseos.com"
DEFAULT_USER_AGENT = "WyseMatePython/0.1.0"
DEFAULT_TIMEOUT = 30  # seconds

# HTTP Headers
HEADER_API_KEY = "x-api-key"
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

# File upload
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = [
    "text/plain",
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/json",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]

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
SESSION_STATUS_RUNNING = "running"
SESSION_STATUS_PAUSED = "paused"
SESSION_STATUS_STOPPED = "stopped"
SESSION_STATUS_ENDED = "ended"
SESSION_STATUS_ERROR = "error"

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
