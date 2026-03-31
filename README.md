# WyseOS SDK for Python

Official Python SDK for WyseOS session protocol and real-time task execution.

## Highlights

- HTTP + WebSocket workflow aligned with `docs/wyse-session-protocol.md`
- `CreateSessionRequest(task, mode, platform, extra)`
- API Key and JWT dual authentication
- `TaskRunner` for automated and interactive execution
- Marketing rich-stream support (`marketing_tweet_reply`, `marketing_tweet_interact`, `writer_twitter`)
- Marketing data APIs and dashboard APIs

## Installation

```bash
pip install wyseos-sdk
```

See full install guide: `installation.md`.

## Quick Start

```python
from wyseos.mate import Client, create_task_runner
from wyseos.mate.config import load_config
from wyseos.mate.models import CreateSessionRequest
from wyseos.mate.task_runner import TaskExecutionOptions, TaskMode
from wyseos.mate.websocket import WebSocketClient

# 1) Initialize client
client = Client(load_config("mate.yaml"))

# 2) Create session (latest protocol fields)
req = CreateSessionRequest(
    task="Draft a Twitter launch campaign for my product",
    mode="marketing",
    platform="api",
    extra={"marketing_product": {"product_id": "prod_123"}},
)
session = client.session.create(req)
session_info = client.session.get_info(session.session_id)

# 3) Connect websocket + task runner
ws_client = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key or "",
    jwt_token=client.jwt_token or "",
    session_id=session_info.session_id,
)
task_runner = create_task_runner(ws_client, client, session_info)

# 4) Execute interactive session (recommended for marketing input loops)
task_runner.run_interactive_session(
    initial_task="Generate 3 tweet drafts and 5 candidate replies",
    task_mode=TaskMode.Marketing,
    extra=req.extra,
    options=TaskExecutionOptions(
        auto_accept_plan=False,
        verbose=True,
        stop_on_x_confirm=True,
        completion_timeout=600,
    ),
)
```

More examples: `examples/quickstart.md` and `examples/getting_started/example.py`.

## Authentication

Use one of the following in `ClientOptions` / `mate.yaml`:

- `api_key`
- `jwt_token`

Behavior:

- HTTP:
  - `api_key` -> `x-api-key`
  - `jwt_token` -> `Authorization`
- WebSocket URL query:
  - `?api_key=...`
  - `?authorization=...`

## Session Protocol Flow

Typical flow:

1. `client.session.create(...)` to get `session_id`
2. Connect `WebSocketClient`
3. Send `start`
4. Receive `plan / input / progress / rich / text`
5. Receive `task_result`
6. Optionally receive `follow_up_suggestion`

For full message schema and rich types, see `docs/wyse-session-protocol.md`.

## Task Runner API

`TaskRunner` is created via:

```python
task_runner = create_task_runner(ws_client, client, session_info)
```

Main methods:

- `run_task(task, attachments=None, task_mode=TaskMode.Default, extra=None, options=None) -> TaskResult`
- `run_interactive_session(initial_task, attachments=None, task_mode=TaskMode.Default, extra=None, options=None)`

`TaskExecutionOptions` includes:

- `verbose` (default: `False`) — print status/progress to stdout
- `auto_accept_plan` — auto-approve plan without user input
- `capture_screenshots`
- `stop_on_x_confirm` — stop session when browser confirmation is requested (useful in CLI)
- `completion_timeout`

## Marketing APIs

Session-scoped generated content:

```python
client.session.get_marketing_data(session_id, type="reply")
client.session.get_marketing_data(session_id, type="like")
client.session.get_marketing_data(session_id, type="retweet")
client.session.get_marketing_data(session_id, type="tweet")
```

Dashboard APIs:

```python
client.marketing.get_product_info(product_id)
client.marketing.get_report_detail(report_id)
client.marketing.update_report(report_id, data)
client.marketing.get_research_tweets(query_id)
```

## Services Overview

- `client.user` - API keys
- `client.team` - team list/info
- `client.agent` - agent list/info
- `client.session` - create/info/messages/marketing data
- `client.browser` - browser APIs
- `client.file_upload` - upload and validation
- `client.marketing` - dashboard marketing APIs

## Error Types

- `APIError`
- `NetworkError`
- `WebSocketError`
- `ConfigError`
- `SessionExecutionError`

## Documentation

- Protocol: `docs/wyse-session-protocol.md`
- Upgrade notes: `docs/session_protocol_upgrade.md`
- Quick Start: `examples/quickstart.md`
- Installation: `installation.md`
- Full Example: `examples/getting_started/example.py`
