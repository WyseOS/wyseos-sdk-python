# AGENTS Guide

AI agent guidance for `mate-sdk-python`. See `README.md` for user-facing docs.

## How To Use

This SDK supports two independent modes and they should be used separately.

1. Install: `pip install wyseos-sdk`
2. Configure `mate.yaml` with `api_key` or `jwt_token`：

```yaml
   mate:
     api_key: "your-api-key"
     # or jwt_token: "your-jwt-token"
     base_url: "https://api.wyseos.com"
     timeout: 30
   ```
3. Initialize client:


```python
from wyseos.mate import Client
from wyseos.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

4. Pick one mode below.

### Marketing Mode

Use this mode for interactive generation loops (tweet/reply/like/retweet) over WebSocket sessions.

```python
from wyseos.mate import Client, create_task_runner
from wyseos.mate.config import load_config
from wyseos.mate.models import CreateSessionRequest
from wyseos.mate.task_runner import TaskExecutionOptions, TaskMode
from wyseos.mate.websocket import WebSocketClient

client = Client(load_config("mate.yaml"))
req = CreateSessionRequest(task="Create launch tweets", mode="marketing", platform="api", extra={})
session = client.session.create(req)
session_info = client.session.get_info(session.session_id)

ws = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key or "",
    jwt_token=client.jwt_token or "",
    session_id=session_info.session_id,
)
runner = create_task_runner(ws, client, session_info)
runner.run_interactive_session(
    initial_task="Generate 3 tweet drafts",
    task_mode=TaskMode.Marketing,
    extra=req.extra,
    options=TaskExecutionOptions(verbose=True),
)
```

Example: [Marketing Example](examples/getting_started/example.py)

### Product Analysis Mode

Use this mode for create-product, polling, and report retrieval over HTTP APIs.

```python
from wyseos.mate import Client
from wyseos.mate.config import load_config

client = Client(load_config("mate.yaml"))
report = client.product.create_and_wait(product="Notion")
print(report.report_id, report.product_name)
```

Example: [Product Analysis Example](examples/product_analysis/example.py)

## Repository Structure

```text
.
├── README.md                  # Main user-facing documentation (English)
├── README_cn.md               # Main user-facing documentation (Chinese)
├── installation.md            # Installation guide (English)
├── installation_cn.md         # Installation guide (Chinese)
├── docs/                      # Protocol and API docs
├── examples/                  # Runnable examples and quick-start docs
└── wyseos/                    # Python package source
    ├── __init__.py            # Package entry
    └── mate/                  # Core SDK module
        ├── client.py          # Top-level client and service wiring
        ├── config.py          # Config loading and parsing
        ├── constants.py       # Shared protocol/API constants
        ├── errors.py          # Exception types
        ├── factory.py         # TaskRunner factory helpers
        ├── models.py          # Request/response models
        ├── plan.py            # Plan-related models
        ├── task_runner.py     # Interactive and automated task execution
        ├── websocket.py       # WebSocket transport client
        └── services/          # Domain services (session/product/marketing/etc.)
```

## Architecture

```mermaid
flowchart LR
    App[User App] --> Client[Client]
    Client --> Session[SessionService]
    Client --> Product[ProductService]
    Client --> Marketing[MarketingService]
    Client --> Upload[FileUploadService]
    Session --> HTTP[HTTP API]
    Product --> HTTP
    Marketing --> HTTP
    Upload --> HTTP
    Session --> Runner[TaskRunner]
    Runner --> WS[WebSocketClient]
    WS --> WSS[WebSocket]
```

## Key Features

- HTTP + WebSocket session workflow
- Dual authentication (`api_key` and `jwt_token`)
- Interactive and automated execution via `TaskRunner`
- Product analysis flow (`create`, `poll`, `report`, `create_and_wait`)
- Marketing session and dashboard APIs
- File upload APIs for attachment-based workflows

## Versioning

- Package version is defined in `pyproject.toml` (`[project].version`).
- Runtime SDK version fields exist in:
  - `wyseos/mate/__init__.py` (`__version__`)
  - `wyseos/mate/client.py` (`self.user_agent`)
- When bumping versions, keep these values aligned in the same change.
