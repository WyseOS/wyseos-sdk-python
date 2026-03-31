# WyseOS Skill

## Metadata

| Field      | Value                                       |
| ---------- | ------------------------------------------- |
| Name       | wyseos                                      |
| Version    | 0.3.1                                       |
| Package    | `wyseos-sdk`                              |
| Python     | >= 3.9                                      |
| Author     | Wyse (info@wyseos.com)                      |
| License    | See LICENSE                                 |
| Repository | https://github.com/WyseOS/wyseos-sdk-python |
| PyPI       | https://pypi.org/project/wyseos-sdk/        |

## Introduction

WyseOS Python SDK provides session protocol and real-time task execution capabilities for two core scenarios: **Marketing** (interactive tweet/reply generation via WebSocket) and **Product Analysis** (create product, poll status, retrieve report via HTTP). 

The SDK supports API Key / JWT dual authentication, streaming rich content, and an automated TaskRunner for both headless and interactive workflows.

## Installation

```bash
pip install wyseos-sdk
```

Or install from source:

```bash
git clone https://github.com/WyseOS/wyseos-sdk-python
cd wyseos-sdk-python
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e .
```

### Configuration

Create `mate.yaml` in your project root:

```yaml
mate:
  api_key: "your-api-key"       # or use jwt_token
  base_url: "https://api.wyseos.com"
  timeout: 30
```

Initialize client:

```python
from wyseos.mate import Client
from wyseos.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

## Marketing Mode

Interactive generation of tweets, replies, likes, and retweets via WebSocket session.

### Usage

```python
from wyseos.mate import Client, create_task_runner
from wyseos.mate.config import load_config
from wyseos.mate.models import CreateSessionRequest
from wyseos.mate.task_runner import TaskExecutionOptions, TaskMode
from wyseos.mate.websocket import WebSocketClient

client = Client(load_config("mate.yaml"))

# Create session
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

# Connect and run
ws_client = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key or "",
    jwt_token=client.jwt_token or "",
    session_id=session_info.session_id,
)
task_runner = create_task_runner(ws_client, client, session_info)

task_runner.run_interactive_session(
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

### Retrieving Marketing Data

```python
reply_data   = client.session.get_marketing_data(session.session_id, type="reply")
tweet_data   = client.session.get_marketing_data(session.session_id, type="tweet")
like_data    = client.session.get_marketing_data(session.session_id, type="like")
retweet_data = client.session.get_marketing_data(session.session_id, type="retweet")
```

### Product Service APIs

```python
client.marketing.get_product_info(product_id)
client.marketing.get_report_detail(report_id)
client.marketing.update_report(report_id, data)
client.marketing.get_research_tweets(query_id)
```

### When to Use

- Generate tweet drafts, reply templates, or retweet/like strategies for a product launch
- Run interactive marketing content creation loops with human review
- Retrieve and manage generated marketing assets per session

## Product Analysis Mode

Create a product, poll until analysis completes, and retrieve the full report. Pure HTTP, no WebSocket needed.

### Usage (One-shot)

```python
from wyseos.mate import Client
from wyseos.mate.config import load_config

client = Client(load_config("mate.yaml"))

report = client.product.create_and_wait(
    product="Notion",                       # product name or URL
    on_poll=lambda attempt, status: print(f"[{attempt}] {status}"),
)

print(report.product_name)
print(report.target_description)
print(report.keywords)
print(report.competitors)
print(report.user_personas)
print(report.recommended_campaigns)
```

### Usage (Step-by-step)

```python
from wyseos.mate.models import CreateProductRequest

created = client.product.create(CreateProductRequest(product="Notion"))
info = client.product.get_info(created.product_id)

if info.analysis_result and info.analysis_result.report_id:
    report = client.product.get_report(info.analysis_result.report_id)

# Optional: industry categories
categories = client.product.get_categories()
```

### Optional: Upload Attachments

```python
upload = client.file_upload.upload_file("brief.pdf")
attachments = [{"file_name": upload["file_name"], "file_url": upload["file_url"]}]

report = client.product.create_and_wait(product="Notion", attachments=attachments)
```

### When to Use

- Analyze a product's market positioning, keywords, competitors, and user personas
- Generate structured reports for campaign planning without real-time interaction
- Batch product research workflows where polling is sufficient

## Notes

- **Two independent modes**: Marketing and Product Analysis are separate entry points; do not mix them in a single flow.
- **Authentication**: Provide either `api_key` or `jwt_token` in `mate.yaml`. HTTP uses `x-api-key` / `Authorization` headers; WebSocket passes credentials as URL query parameters.
- **Error handling**: The SDK raises `APIError`, `NetworkError`, `WebSocketError`, `ConfigError`, and `SessionExecutionError`. Wrap calls accordingly.
- **Interactive commands** (Marketing mode): type `stop`, `pause`, `exit` / `quit` / `q` during an interactive session to control execution.
- **TaskExecutionOptions**: Use `verbose=True` for stdout logging, `auto_accept_plan=True` to skip manual plan approval, and `stop_on_x_confirm=True` in CLI/headless environments.
