[English](quickstart.md) | [中文](quickstart_cn.md)

# OctoEvo Python SDK Quick Start

Use this guide to run the two supported SDK workflows:

- **Marketing session**: WebSocket-based interactive task execution for tweet, reply, like, and retweet workflows.
- **Product analysis**: HTTP API workflow for creating a product analysis job, polling status, and reading the final report.

Keep these workflows separate. Marketing tasks use `TaskRunner`; product analysis uses `client.product`.

## Requirements

- Python 3.9+
- An OctoEvo `api_key` or `jwt_token`
- `pip install octoevo`

Never commit real credentials. Put local secrets in `mate.yaml`, environment-specific secret storage, or your CI secret manager.

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install octoevo
```

## Configure

Create `mate.yaml`:

```yaml
mate:
  api_key: "your-api-key"
  # jwt_token: "your-jwt-token"
  base_url: "https://api.dev.weclaw.ai"
  timeout: 30
```

Initialize the client:

```python
from octoevo.mate import Client
from octoevo.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

## Workflow A: Marketing Session

Marketing tasks default to `execution_mode="auto"` in `TaskRunner`. Do not pass `external_user_id` or `external_username`; the agent chooses the execution channel and asks for X authorization, X account selection, or browser extension connection only when required.

```python
from octoevo.mate import Client, create_task_runner
from octoevo.mate.config import load_config
from octoevo.mate.models import CreateSessionRequest
from octoevo.mate.task_runner import TaskExecutionOptions, TaskMode
from octoevo.mate.websocket import WebSocketClient

client = Client(load_config("mate.yaml"))

req = CreateSessionRequest(
    task="Draft a launch thread for my product",
    mode="marketing",
    platform="api",
    extra={
        "marketing_product": {"product_id": "prod_123"},
        "skills": [{"skill_id": "xxx", "skill_name": "persona"}],
    },
)

session = client.session.create(req)
session_info = client.session.get_info(session.session_id)

ws_client = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key or "",
    jwt_token=client.jwt_token or "",
    session_id=session_info.session_id,
)

runner = create_task_runner(ws_client, client, session_info)
runner.run_interactive_session(
    initial_task="Generate 3 tweet drafts and recommended replies",
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

Use `stop_on_x_confirm=True` for a safe CLI default: the session stops instead of confirming a live social action. Set it to `False` only when your application is expected to confirm execution automatically.

During `run_interactive_session()`, the SDK handles these structured prompts:

| Prompt | Meaning | SDK behavior |
| --- | --- | --- |
| `x_api_authorize` | X API authorization is required | Prints the authorization URL, then resumes after you press Enter |
| `x_api_account_select` | Multiple X accounts are connected | Shows account choices and sends the selected account for this session |
| `extension_required` | Browser extension is required | Prints the extension connection URL and waits for acknowledgement |

After the session, read generated marketing data:

```python
tweet_data = client.session.get_marketing_data(session.session_id, type="tweet")
reply_data = client.session.get_marketing_data(session.session_id, type="reply")

print(len(tweet_data.get("tweet", [])), "draft tweets")
print(len(reply_data.get("reply", [])), "replies")
```

Runnable example: [`getting_started/example.py`](getting_started/example.py)

## Workflow B: Product Analysis

Product analysis is pure HTTP. It does not use WebSocket or `TaskRunner`.

```python
from octoevo.mate import Client
from octoevo.mate.config import load_config

client = Client(load_config("mate.yaml"))

report = client.product.create_and_wait(
    product="Notion",  # product name or URL
    attachments=None,
    on_poll=lambda attempt, status: print(f"[poll {attempt}] {status}"),
)

print("report_id:", report.report_id)
print("product_name:", report.product_name)
print("keywords:", report.keywords)
print("competitors:", report.competitors)
```

For attachments, upload files first and pass the upload response values:

```python
upload = client.file_upload.upload_file("brief.pdf")
attachments = [{"file_name": upload["file_name"], "file_url": upload["file_url"]}]

report = client.product.create_and_wait(
    product="Notion",
    attachments=attachments,
)
```

Runnable example: [`product_analysis/example.py`](product_analysis/example.py)

## Optional: Account Bootstrap

These helpers are standalone account flows. They are not needed inside normal marketing task execution.

```python
from octoevo.mate import Client, ClientOptions

client = Client(ClientOptions())

email_resp = client.user.start_email_verification(
    email="you@example.com",
    invite_code=None,
)
print(email_resp.sign_type, email_resp.pre_auth_id)

x_login = client.user.get_x_oauth_url()
print(x_login.auth_url)
```

Low-level X connector management requires an authenticated client:

```python
accounts = client.user.list_x_accounts()
auth = client.user.authorize_x_account(target_connector_id=None)
print(len(accounts.items), auth.auth_url)

client.user.delete_x_account("connector-id")
```

Use these connector APIs only for account administration. Do not use them to choose a task execution account; `run_interactive_session()` handles task-time authorization and account selection.

Runnable examples:

- [`auth/auth_example.py`](auth/auth_example.py)
- [`auth/connectors_example.py`](auth/connectors_example.py)

## Error Handling

```python
from octoevo.mate.errors import APIError, ConfigError, NetworkError, WebSocketError

try:
    # SDK calls
    pass
except APIError as exc:
    print("API error:", exc)
except WebSocketError as exc:
    print("WebSocket error:", exc)
except NetworkError as exc:
    print("Network error:", exc)
except ConfigError as exc:
    print("Config error:", exc)
```

For marketing tasks that may need user input, prefer `run_interactive_session()`. Non-interactive `run_task()` fails safely when authorization, account selection, or browser extension connection is required.

## More References

- Main README: [`../README.md`](../README.md)
- Installation: [`../installation.md`](../installation.md)
- Marketing example: [`getting_started/example.py`](getting_started/example.py)
- Product analysis example: [`product_analysis/example.py`](product_analysis/example.py)
