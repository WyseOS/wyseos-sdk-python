[English](quickstart.md) | [中文](quickstart_cn.md)

# 快速开始指南

这个 SDK 有 **两个独立场景**：

* **营销场景（WebSocket + Session APIs）**

  用于交互式生成循环（tweet/reply/like/retweet 流程）。
* **产品分析（HTTP 轮询 + Product APIs）**

  用于创建产品、轮询状态和获取最终报告。

二者是独立入口，不混用。

## 1. 环境准备

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install wyseos-sdk
```

## 2. 配置客户端

创建 `mate.yaml`：

```yaml
mate:
  api_key: "your-api-key"
  # or jwt_token: "your-jwt-token"
  base_url: "https://api.wyseos.com"
  timeout: 30
```

初始化：

```python
from wyseos.mate import Client
from wyseos.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

## 3. 选择一个工作流

| 工作流   | 入口                                                     | 传输方式  | 主要输出                |
| -------- | -------------------------------------------------------- | --------- | ----------------------- |
| 营销会话 | `create_task_runner(...).run_interactive_session(...)` | WebSocket | 流式会话消息 + 营销数据 |
| 产品分析 | `client.product.create_and_wait(...)`                  | HTTP 轮询 | `ProductReport`       |

---

## A) 营销会话（独立流程）

### A1. 创建会话

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

### A2. 运行交互式会话

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

### A3. 读取营销数据

```python
reply_data = client.session.get_marketing_data(session.session_id, type="reply")
like_data = client.session.get_marketing_data(session.session_id, type="like")
retweet_data = client.session.get_marketing_data(session.session_id, type="retweet")
tweet_data = client.session.get_marketing_data(session.session_id, type="tweet")

print(len(reply_data.get("reply", [])), "replies")
print(len(tweet_data.get("tweet", [])), "draft tweets")
```

交互命令：

- `stop` -> 发送停止消息
- `pause` -> 发送暂停消息
- `exit` / `quit` / `q` -> 退出会话

### A4. 停止会话（HTTP 或 WebSocket）

结束进行中的会话有两种方式：

1. **HTTP 接口** — 不依赖 WebSocket，使用创建会话时得到的 `session_id`：

```python
client.session.stop(session.session_id)
```

2. **WebSocket** — 在已连接的前提下：

```python
ws_client.send_stop()
```

交互式命令行里输入 `stop` 与调用 `send_stop()` 等价：都会通过 WebSocket 发送 `type: "stop"` 的消息。HTTP 的 `stop` 则通过 REST 通知服务端结束该会话。

---

## B) 产品分析（独立流程）

### B1. 可选：上传附件

将上传响应作为 `attachments` 的可信来源：

```python
upload = client.file_upload.upload_file("brief.pdf")
attachments = [{"file_name": upload["file_name"], "file_url": upload["file_url"]}]
```

### B2. 一步式 API（推荐）

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

### B3. 分步 API

```python
from wyseos.mate.models import CreateProductRequest

created = client.product.create(
    CreateProductRequest(product="Notion", attachments=attachments)
)
info = client.product.get_info(created.product_id)

if info.analysis_result and info.analysis_result.report_id:
    report = client.product.get_report(info.analysis_result.report_id)
```

可运行示例：`examples/product_analysis/example.py`。

---

## 4. 错误处理

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

## 5. 相关 API

营销：

- `client.session.stop(session_id)`
- `client.session.get_marketing_data(...)`
- `client.marketing.update_report(report_id, data)`
- `client.marketing.get_research_tweets(query_id)`

产品分析：

- `client.product.create(request)`
- `client.product.create_and_wait(product, attachments=None, ...)`
- `client.product.get_info(product_id)`
- `client.product.get_report(report_id)`
- `client.product.get_categories()`
