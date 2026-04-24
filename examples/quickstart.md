[English](quickstart.md) | [中文](quickstart_cn.md)

# Quick Start Guide

This SDK has **two independent scenarios**:

* **Marketing (WebSocket + Session APIs)**

    For interactive generation loops (tweet/reply/like/retweet flows).

* **Product Analysis (HTTP Polling + Product APIs)** 

    For create-product, poll status, and get final report.

They are separate entry points and should not be mixed.

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

## 3. Register an Account (Two Ways)

Sign-in and sign-up both start without `api_key` or `jwt_token` on the client (these endpoints use `skip_auth=True`). You can use `Client(ClientOptions())` for the default `base_url`, or `load_config("mate.yaml")` if you only need a custom `base_url`.

1. **Email magic link** — send a link to the address; the user opens it in a browser to finish sign-in or sign-up:

```python
from wyseos.mate import Client, ClientOptions

client = Client(ClientOptions())  # or load_config("mate.yaml") without credentials

resp = client.user.start_email_verification(
    email="you@example.com",
    invite_code=None,  # optional invite code
)
# resp.sign_type, resp.pre_auth_id — use after the user follows the link per product flow
```

2. **X (Twitter) OAuth** — get a login URL; open it in a browser to complete sign-in or sign-up with X:

```python
url_resp = client.user.get_x_oauth_url()
print(url_resp.auth_url)  # open in browser
```

Runnable reference: `examples/auth/auth_example.py`.

## 4. X (Twitter) Authorization: Functions

Distinguish **account login/registration** (no API key) from **binding X to an existing account** (requires `api_key` or `jwt_token` after you are signed in).

| Purpose | Call | Auth required |
| ------- | ---- | ------------- |
| Sign in / sign up with X | `client.user.get_x_oauth_url()` | No |
| List connected X accounts | `client.user.list_x_accounts()` | Yes |
| Bind or re-bind an X account (connector) | `client.user.authorize_x_account(target_credential_id=None)` | Yes; optional `target_credential_id` selects the credential slot |
| Remove a connected X account | `client.user.delete_x_account(connector_id)` | Yes |

`authorize_x_account` returns an `OAuthURLResponse` with `auth_url` — open that URL in a browser to complete the connector flow.

Runnable reference: `examples/auth/connectors_example.py`.

## 5. Choose One Workflow

| Workflow          | Entry Point                                              | Transport    | Main Output                                |
| ----------------- | -------------------------------------------------------- | ------------ | ------------------------------------------ |
| Marketing Session | `create_task_runner(...).run_interactive_session(...)` | WebSocket    | Streamed session messages + marketing data |
| Product Analysis  | `client.product.create_and_wait(...)`                  | HTTP polling | `ProductReport`                          |

---

## A) Marketing Session (Independent Flow)

### A1. Create Session

```python
from wyseos.mate.models import CreateSessionRequest

req = CreateSessionRequest(
    task="Create a marketing tweet thread for my product",
    mode="marketing",
    platform="api",
    extra={
        "marketing_product": {"product_id": "prod_123"},
        "skills": [{"skill_id": "xxx", "skill_name": "persona"}],
    },
)

session = client.session.create(req)
session_info = client.session.get_info(session.session_id)
print("session_id:", session.session_id)
```

### A2. Run Interactive Session

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

### A3. Read Marketing Data

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

### A4. Stop Session (HTTP or WebSocket)

You can stop a running session in two ways:

1. **HTTP API** — no WebSocket required; use the same `session_id` you created earlier:

```python
client.session.stop(session.session_id)
```

2. **WebSocket** — while connected:

```python
ws_client.send_stop()
```

In the interactive CLI, typing `stop` is equivalent to `send_stop()`: both send a WebSocket message with `type: "stop"`. The HTTP `stop` endpoint notifies the server to end the session over the REST API.

---

## B) Product Analysis (Independent Flow)

### B1. Optional: Upload Attachments

Use upload response as the source of truth for `attachments`:

```python
upload = client.file_upload.upload_file("brief.pdf")
attachments = [{"file_name": upload["file_name"], "file_url": upload["file_url"]}]
```

### B2. One-shot API (Recommended)

```python
report = client.product.create_and_wait(
    product="Notion",      # product name or URL
    attachments=attachments,  # can be None
    poll_interval=20,      # default
    max_attempts=30,       # default: 10 minutes
)

print("report_id:", report.report_id)
print("status:", report.status)
print("product_name:", report.product_name)
```

### B3. Step-by-step API

```python
from wyseos.mate.models import CreateProductRequest

created = client.product.create(
    CreateProductRequest(product="Notion", attachments=attachments)
)
info = client.product.get_info(created.product_id)

if info.analysis_result and info.analysis_result.report_id:
    report = client.product.get_report(info.analysis_result.report_id)
```

Runnable example: `examples/product_analysis/example.py`.

---

## 6. Error Handling

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

## 7. Related APIs

Account registration (no `api_key` / `jwt_token` required):

- `client.user.start_email_verification(email, invite_code=None)`
- `client.user.get_x_oauth_url()`

X connector (after sign-in, with `api_key` or `jwt_token`):

- `client.user.list_x_accounts()`
- `client.user.authorize_x_account(target_credential_id=None)`
- `client.user.delete_x_account(connector_id)`

Marketing:

- `client.session.stop(session_id)`
- `client.session.get_marketing_data(...)`
- `client.marketing.update_report(report_id, data)`
- `client.marketing.get_research_tweets(query_id)`

Product analysis:

- `client.product.create(request)`
- `client.product.create_and_wait(product, attachments=None, ...)`
- `client.product.get_info(product_id)`
- `client.product.get_report(report_id)`
- `client.product.get_categories()`
