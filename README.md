[English](README.md) | [中文](README_cn.md)

# OctoEvo SDK for Python

Python SDK for OctoEvo agent sessions, marketing execution, and product analysis.

## Features

- HTTP client for sessions, products, files, users, teams, agents, and marketing APIs
- WebSocket `TaskRunner` for interactive and automated agent sessions
- Marketing tasks default to `execution_mode="auto"` so the backend chooses the correct execution channel
- Structured handling for X authorization, X account selection, and browser extension requirements
- Product analysis workflow with create, poll, and report APIs
- API key and JWT authentication

## Requirements

- Python 3.9+
- An OctoEvo `api_key` or `jwt_token`

## Installation

```bash
pip install octoevo
```

For environment-specific setup, see [installation.md](installation.md).

## Configuration

Create `mate.yaml`:

```yaml
mate:
  api_key: "your-api-key"
  # jwt_token: "your-jwt-token"
  base_url: "https://api.dev.weclaw.ai"
  timeout: 30
```

Initialize a client:

```python
from octoevo.mate import Client
from octoevo.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

Never commit real credentials. Use local config files, environment secret storage, or CI secrets.

## Quick Start: Marketing Session

Use `run_interactive_session()` for marketing tasks that may require user input, X authorization, X account selection, or browser extension connection.

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
    extra={"marketing_product": {"product_id": "prod_123"}},
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

Marketing tasks default to `execution_mode="auto"` in `TaskRunner`. Do not pass `external_user_id` or `external_username`; the agent selects the execution channel and asks for required input only when needed.

Structured prompts handled by the SDK:

| Prompt | Meaning |
| --- | --- |
| `x_api_authorize` | X API authorization is required |
| `x_api_account_select` | Multiple X accounts are connected and one must be selected |
| `extension_required` | The browser extension is required for the current action |

Use `stop_on_x_confirm=True` for CLI-safe runs. Set it to `False` only when your app should confirm live social actions automatically.

Read generated marketing data:

```python
tweet_data = client.session.get_marketing_data(session.session_id, type="tweet")
reply_data = client.session.get_marketing_data(session.session_id, type="reply")
```

Runnable example: [examples/getting_started/example.py](examples/getting_started/example.py)

## Product Analysis

Product analysis is HTTP-only. It does not use WebSocket or `TaskRunner`.

```python
from octoevo.mate import Client
from octoevo.mate.config import load_config

client = Client(load_config("mate.yaml"))

report = client.product.create_and_wait(
    product="Notion",
    attachments=None,
    on_poll=lambda attempt, status: print(f"[poll {attempt}] {status}"),
)

print(report.report_id)
print(report.product_name)
print(report.keywords)
print(report.competitors)
```

For attachments, upload files first:

```python
upload = client.file_upload.upload_file("brief.pdf")
attachments = [{"file_name": upload["file_name"], "file_url": upload["file_url"]}]

report = client.product.create_and_wait(
    product="Notion",
    attachments=attachments,
)
```

Runnable example: [examples/product_analysis/example.py](examples/product_analysis/example.py)

## Account Bootstrap

These helpers are standalone account flows. They are not required inside normal marketing task execution.

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

Use connector APIs only for account administration. Do not use them to choose a task execution account; `run_interactive_session()` handles task-time authorization and account selection.

Runnable examples:

- [examples/auth/auth_example.py](examples/auth/auth_example.py)
- [examples/auth/connectors_example.py](examples/auth/connectors_example.py)

## Task Runner API

Create a task runner with:

```python
runner = create_task_runner(ws_client, client, session_info)
```

Main methods:

- `run_interactive_session(initial_task, attachments=None, task_mode=TaskMode.Default, extra=None, options=None)`
- `run_task(task, attachments=None, task_mode=TaskMode.Default, extra=None, options=None) -> TaskResult`

Prefer `run_interactive_session()` for marketing tasks. Non-interactive `run_task()` fails safely when authorization, account selection, or browser extension connection is required.

Common options:

- `verbose`: print progress to stdout
- `auto_accept_plan`: auto-approve plan messages
- `stop_on_x_confirm`: stop instead of confirming social actions
- `completion_timeout`: maximum run time in seconds

## Services

- `client.session`: create sessions, stop sessions, read messages, read marketing data
- `client.product`: create product analysis jobs, poll status, read reports, read categories
- `client.file_upload`: upload files for attachments
- `client.user`: account bootstrap, API keys, X connector management
- `client.marketing`: marketing dashboard APIs
- `client.team`, `client.agent`, `client.browser`: supporting APIs

## Error Types

- `APIError`
- `NetworkError`
- `WebSocketError`
- `ConfigError`
- `SessionExecutionError`

## Documentation

- Quick start: [examples/quickstart.md](examples/quickstart.md)
- Installation: [installation.md](installation.md)
- Marketing example: [examples/getting_started/example.py](examples/getting_started/example.py)
- Product analysis example: [examples/product_analysis/example.py](examples/product_analysis/example.py)
