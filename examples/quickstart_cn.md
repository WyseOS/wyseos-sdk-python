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
pip install octoevo
```

## 2. 配置客户端

创建 `mate.yaml`：

```yaml
mate:
  api_key: "your-api-key"
  # or jwt_token: "your-jwt-token"
  base_url: "https://api.octoevo.ai"
  timeout: 30
```

初始化：

```python
from octoevo.mate import Client
from octoevo.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

## 3. 注册账户（两种方式）

登录与注册都可在**不提供** `api_key`、`jwt_token` 的情况下发起（这些接口在 SDK 中走 `skip_auth`）。无密钥时可用 `Client(ClientOptions())` 使用默认 `base_url`，或仅用 `load_config("mate.yaml")` 配置自定义 `base_url`。

1. **邮箱 magic link** — 向邮箱发送登录/注册链接，用户在浏览器中打开完成验证：

```python
from octoevo.mate import Client, ClientOptions

client = Client(ClientOptions())  # 或使用不含密钥的 mate.yaml

resp = client.user.start_email_verification(
    email="you@example.com",
    invite_code=None,  # 可选填邀请码
)
# resp.sign_type、resp.pre_auth_id — 用户点击邮件内链接后按产品流程续接
```

2. **X（Twitter）OAuth** — 获取用于登录/注册的授权 URL，在浏览器中打开完成：

```python
url_resp = client.user.get_x_oauth_url()
print(url_resp.auth_url)  # 在浏览器中打开
```

可运行参考：`examples/auth/auth_example.py`。

## 4. 授权与绑定 X（相关函数）

区分两类场景：**账户登录/注册**（无 API 密钥）与**将 X 账号绑定到已有账户**（登录后使用 `api_key` 或 `jwt_token`）。

| 用途 | 调用 | 是否需要已登录 |
| ---- | ---- | -------------- |
| 使用 X 登录或注册 | `client.user.get_x_oauth_url()` | 否 |
| 列出已绑定的 X 账号 | `client.user.list_x_accounts()` | 是 |
| 发起绑定或换绑 X（连接器） | `client.user.authorize_x_account(target_connector_id=None)` | 是；可选 `target_connector_id` 指定要写入的凭据位 |
| 解绑已连接的 X 账号 | `client.user.delete_x_account(connector_id)` | 是 |

`authorize_x_account` 返回 `OAuthURLResponse`，通过 `auth_url` 在浏览器中完成授权。

可运行参考：`examples/auth/connectors_example.py`。

## 5. 选择一个工作流

| 工作流   | 入口                                                     | 传输方式  | 主要输出                |
| -------- | -------------------------------------------------------- | --------- | ----------------------- |
| 营销会话 | `create_task_runner(...).run_interactive_session(...)` | WebSocket | 流式会话消息 + 营销数据 |
| 产品分析 | `client.product.create_and_wait(...)`                  | HTTP 轮询 | `ProductReport`       |

---

## A) 营销会话（独立流程）

### A1. 创建会话

```python
from octoevo.mate.models import CreateSessionRequest

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
from octoevo.mate import create_task_runner
from octoevo.mate.task_runner import TaskExecutionOptions, TaskMode
from octoevo.mate.websocket import WebSocketClient

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
from octoevo.mate.models import CreateProductRequest

created = client.product.create(
    CreateProductRequest(product="Notion", attachments=attachments)
)
info = client.product.get_info(created.product_id)

if info.analysis_result and info.analysis_result.report_id:
    report = client.product.get_report(info.analysis_result.report_id)
```

可运行示例：`examples/product_analysis/example.py`。

---

## 6. 错误处理

```python
from octoevo.mate.errors import APIError, NetworkError, ConfigError, WebSocketError

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

## 7. 相关 API

账户注册（不需要 `api_key` / `jwt_token`）：

- `client.user.start_email_verification(email, invite_code=None)`
- `client.user.get_x_oauth_url()`

X 连接器（登录后、带 `api_key` 或 `jwt_token`）：

- `client.user.list_x_accounts()`
- `client.user.authorize_x_account(target_connector_id=None)`
- `client.user.delete_x_account(connector_id)`

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
