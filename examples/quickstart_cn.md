[English](quickstart.md) | [中文](quickstart_cn.md)

# OctoEvo Python SDK 快速开始

本指南覆盖 SDK 的两个主要工作流：

- **营销会话**：基于 WebSocket 的交互式任务执行，用于 tweet、reply、like、retweet 等流程。
- **产品分析**：基于 HTTP API 的产品分析任务创建、状态轮询和报告读取。

两个工作流相互独立。营销任务使用 `TaskRunner`；产品分析使用 `client.product`。

## 环境要求

- Python 3.9+
- OctoEvo `api_key` 或 `jwt_token`
- `pip install octoevo`

不要提交真实密钥。请把本地密钥放在 `mate.yaml`、环境专用 Secret 存储或 CI Secret Manager 中。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install octoevo
```

## 配置

创建 `mate.yaml`：

```yaml
mate:
  api_key: "your-api-key"
  # jwt_token: "your-jwt-token"
  base_url: "https://api.dev.weclaw.ai"
  timeout: 30
```

初始化客户端：

```python
from octoevo.mate import Client
from octoevo.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

## 工作流 A：营销会话

营销任务会在 `TaskRunner` 内默认使用 `execution_mode="auto"`。调用方不要传 `external_user_id` 或 `external_username`；agent 会自行选择执行通道，并且只在必要时请求 X 授权、X 账号选择或浏览器插件连接。

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

`stop_on_x_confirm=True` 是更安全的 CLI 默认值：当任务请求确认真实社交动作时，SDK 会停止会话而不是自动确认。只有当你的应用明确需要自动确认执行时，才设置为 `False`。

在 `run_interactive_session()` 中，SDK 会处理这些结构化提示：

| 提示 | 含义 | SDK 行为 |
| --- | --- | --- |
| `x_api_authorize` | 需要 X API 授权 | 打印授权 URL，用户完成授权后按回车继续 |
| `x_api_account_select` | 当前用户连接了多个 X 账号 | 展示账号列表，并把本次会话选择回传给 agent |
| `extension_required` | 当前动作必须使用浏览器插件 | 打印插件连接 URL，并等待用户确认 |

会话结束后读取营销数据：

```python
tweet_data = client.session.get_marketing_data(session.session_id, type="tweet")
reply_data = client.session.get_marketing_data(session.session_id, type="reply")

print(len(tweet_data.get("tweet", [])), "draft tweets")
print(len(reply_data.get("reply", [])), "replies")
```

可运行示例：[`getting_started/example.py`](getting_started/example.py)

## 工作流 B：产品分析

产品分析是纯 HTTP 流程，不使用 WebSocket 或 `TaskRunner`。

```python
from octoevo.mate import Client
from octoevo.mate.config import load_config

client = Client(load_config("mate.yaml"))

report = client.product.create_and_wait(
    product="Notion",  # 产品名或 URL
    attachments=None,
    on_poll=lambda attempt, status: print(f"[poll {attempt}] {status}"),
)

print("report_id:", report.report_id)
print("product_name:", report.product_name)
print("keywords:", report.keywords)
print("competitors:", report.competitors)
```

如需附件，先上传文件，再使用上传响应中的字段：

```python
upload = client.file_upload.upload_file("brief.pdf")
attachments = [{"file_name": upload["file_name"], "file_url": upload["file_url"]}]

report = client.product.create_and_wait(
    product="Notion",
    attachments=attachments,
)
```

可运行示例：[`product_analysis/example.py`](product_analysis/example.py)

## 可选：账户引导

这些接口是独立账户流程，不是普通营销任务执行的必需步骤。

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

低层 X 连接器管理需要已认证的客户端：

```python
accounts = client.user.list_x_accounts()
auth = client.user.authorize_x_account(target_connector_id=None)
print(len(accounts.items), auth.auth_url)

client.user.delete_x_account("connector-id")
```

这些连接器 API 只用于账号管理。不要用它们为任务选择执行账号；`run_interactive_session()` 会处理任务期授权和账号选择。

可运行示例：

- [`auth/auth_example.py`](auth/auth_example.py)
- [`auth/connectors_example.py`](auth/connectors_example.py)

## 错误处理

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

对于可能需要用户输入的营销任务，优先使用 `run_interactive_session()`。非交互式 `run_task()` 在遇到授权、账号选择或浏览器插件连接需求时会安全失败。

## 更多参考

- 主 README：[`../README_cn.md`](../README_cn.md)
- 安装说明：[`../installation_cn.md`](../installation_cn.md)
- 营销示例：[`getting_started/example.py`](getting_started/example.py)
- 产品分析示例：[`product_analysis/example.py`](product_analysis/example.py)
