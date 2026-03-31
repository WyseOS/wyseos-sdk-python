# Quick Start Guide

This guide follows the latest session protocol in `../docs/wyse-session-protocol.md`.

## 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install wyseos-sdk
```

## 2. Configure Client

Create `mate.yaml`:

```yaml
mate:
  api_key: "your-api-key"
  # or jwt_token: "your-jwt-token"
  base_url: "https://api.wyseos.com"
  timeout: 30
```

Initialize:

```python
from wyseos.mate import Client
from wyseos.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

## 3. Create Session

`CreateSessionRequest` uses `task/mode/platform/extra`.

```python
from wyseos.mate.models import CreateSessionRequest

req = CreateSessionRequest(
    task="Create a marketing tweet thread for my product",
    mode="marketing",      # optional
    platform="api",        # optional
    extra={                 # optional
        "marketing_product": {"product_id": "prod_123"},
        "skills": [{"skill_id": "xxx", "skill_name": "persona"}],
    },
)

session = client.session.create(req)
session_info = client.session.get_info(session.session_id)
print("session_id:", session.session_id)
```

## 4. Run Interactive Session (Marketing)

```python
from wyseos.mate import create_task_runner
from wyseos.mate.task_runner import TaskExecutionOptions, TaskMode
from wyseos.mate.websocket import WebSocketClient

ws_client = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key or "",
    jwt_token=client.jwt_token or "",
    session_id=session_info.session_id,
)

task_runner = create_task_runner(ws_client, client, session_info)

task_runner.run_interactive_session(
    initial_task="Generate 3 tweet drafts and recommended replies",
    attachments=[],
    task_mode=TaskMode.Marketing,
    extra=req.extra,
    options=TaskExecutionOptions(
        auto_accept_plan=False,
        capture_screenshots=False,
        verbose=True,
        stop_on_x_confirm=True,
        completion_timeout=600,
    ),
)
```

## 5. Read Marketing Output

During marketing rich streaming, SDK will aggregate chunks and fetch final data by type.

You can also query explicitly:

```python
reply_data = client.session.get_marketing_data(session.session_id, type="reply")
like_data = client.session.get_marketing_data(session.session_id, type="like")
retweet_data = client.session.get_marketing_data(session.session_id, type="retweet")
tweet_data = client.session.get_marketing_data(session.session_id, type="tweet")

print(len(reply_data.get("reply", [])), "replies")
print(len(tweet_data.get("tweet", [])), "draft tweets")
```

Interactive commands:

- `stop` -> send stop message
- `pause` -> send pause message
- `exit` / `quit` / `q` -> leave session

## 6. Upload Files

```python
is_valid, msg = client.file_upload.validate_file("brief.pdf")
if is_valid:
    upload = client.file_upload.upload_file("brief.pdf")
    attachments = [{"file_name": "brief.pdf", "file_url": upload["file_url"]}]
```

Then pass `attachments` into `run_interactive_session(...)`.

## 7. Error Handling

```python
from wyseos.mate.errors import APIError, NetworkError, ConfigError, WebSocketError

try:
    # your SDK calls
    pass
except APIError as e:
    print("APIError:", e)
except WebSocketError as e:
    print("WebSocketError:", e)
except NetworkError as e:
    print("NetworkError:", e)
except ConfigError as e:
    print("ConfigError:", e)
```

## 8. Related APIs

- `client.session.get_marketing_data(...)`
- `client.marketing.get_product_info(product_id)`
- `client.marketing.get_report_detail(report_id)`
- `client.marketing.update_report(report_id, data)`
- `client.marketing.get_research_tweets(query_id)`
