---
name: wyseos
description: WyseOS Python SDK for AI-driven marketing content generation and product analysis. Use when building marketing automation (tweet/reply/retweet generation via WebSocket sessions) or product research workflows (market positioning, keywords, competitors, user personas via HTTP polling).
license: See LICENSE
compatibility: Requires Python 3.9+
metadata:
  author: Wyse
  version: "0.3.1"
  package: wyseos-sdk
  repository: https://github.com/WyseOS/wyseos-sdk-python
  pypi: https://pypi.org/project/wyseos-sdk/
---

# WyseOS Skill

WyseOS Python SDK provides two independent workflows: **Marketing Mode** (interactive tweet/reply generation via WebSocket) and **Product Analysis Mode** (create product, poll status, retrieve report via HTTP).

## Installation

```bash
pip install wyseos-sdk
```

Or from source:

```bash
git clone https://github.com/WyseOS/wyseos-sdk-python
cd wyseos-sdk-python
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e .
```

### Initialize Client

```python
from wyseos.mate import Client, ClientOptions

client = Client(ClientOptions(
    api_key="your-api-key",         # or jwt_token="your-jwt-token" (pick one)
    base_url="https://api.wyseos.com",  # required
    timeout=30,                     # optional, default 30s
))
```

## Marketing Mode

Interactive generation of tweets, replies, likes, and retweets via WebSocket session.

### Usage

```python
from wyseos.mate import Client, ClientOptions, create_task_runner
from wyseos.mate.models import CreateSessionRequest
from wyseos.mate.task_runner import TaskExecutionOptions, TaskMode
from wyseos.mate.websocket import WebSocketClient

client = Client(ClientOptions(
    api_key="your-api-key",
    base_url="https://api.wyseos.com",
))

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
        stop_on_x_confirm=False,
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

### Dashboard APIs

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
from wyseos.mate import Client, ClientOptions

client = Client(ClientOptions(
    api_key="your-api-key",
    base_url="https://api.wyseos.com",
))

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
- **Authentication**: Provide either `api_key` or `jwt_token` in `ClientOptions`. HTTP uses `x-api-key` / `Authorization` headers; WebSocket passes credentials as URL query parameters.
- **Error handling**: The SDK raises `APIError`, `NetworkError`, `WebSocketError`, `ConfigError`, and `SessionExecutionError`.
- **Interactive commands** (Marketing mode): type `stop`, `pause`, `exit` / `quit` / `q` during an interactive session to control execution.
- **TaskExecutionOptions**: `verbose=True` for stdout logging, `auto_accept_plan=True` to skip manual plan approval, `stop_on_x_confirm=True` in CLI/headless environments.
