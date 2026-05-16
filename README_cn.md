[English](README.md) | [中文](README_cn.md)

# OctoEvo Python SDK

OctoEvo agent 会话、营销执行和产品分析的 Python SDK。

## 功能

- HTTP client：覆盖 session、product、file、user、team、agent、marketing 等 API
- WebSocket `TaskRunner`：支持交互式和自动化 agent 会话
- 营销任务在 `TaskRunner` 中默认使用 `execution_mode="auto"`，由后端选择执行通道
- 结构化处理 X 授权、X 账号选择和浏览器插件需求
- 产品分析：创建任务、轮询状态、读取报告
- 支持 API key 和 JWT 两种认证方式

## 环境要求

- Python 3.9+
- OctoEvo `api_key` 或 `jwt_token`

## 安装

```bash
pip install octoevo
```

更多环境配置见 [installation_cn.md](installation_cn.md)。

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

不要提交真实密钥。请使用本地配置文件、环境 Secret 存储或 CI Secret。

## 快速开始：营销会话

营销任务如果可能需要用户输入、X 授权、X 账号选择或浏览器插件连接，推荐使用 `run_interactive_session()`。

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

营销任务会在 `TaskRunner` 内默认使用 `execution_mode="auto"`。调用方不要传 `external_user_id` 或 `external_username`；agent 会选择执行通道，并只在必要时请求输入。

SDK 会处理的结构化提示：

| 提示 | 含义 |
| --- | --- |
| `x_api_authorize` | 需要 X API 授权 |
| `x_api_account_select` | 当前用户连接了多个 X 账号，需要选择一个 |
| `extension_required` | 当前动作需要浏览器插件 |

`stop_on_x_confirm=True` 适合作为 CLI 安全默认值：遇到真实社交动作确认时停止，而不是自动确认。只有当你的应用明确需要自动确认执行时，才设置为 `False`。

读取生成的营销数据：

```python
tweet_data = client.session.get_marketing_data(session.session_id, type="tweet")
reply_data = client.session.get_marketing_data(session.session_id, type="reply")
```

可运行示例：[examples/getting_started/example.py](examples/getting_started/example.py)

## 产品分析

产品分析是纯 HTTP 流程，不使用 WebSocket 或 `TaskRunner`。

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

如需附件，先上传文件：

```python
upload = client.file_upload.upload_file("brief.pdf")
attachments = [{"file_name": upload["file_name"], "file_url": upload["file_url"]}]

report = client.product.create_and_wait(
    product="Notion",
    attachments=attachments,
)
```

可运行示例：[examples/product_analysis/example.py](examples/product_analysis/example.py)

## 账户引导

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

低层 X 连接器管理需要已认证客户端：

```python
accounts = client.user.list_x_accounts()
auth = client.user.authorize_x_account(target_connector_id=None)
print(len(accounts.items), auth.auth_url)

client.user.delete_x_account("connector-id")
```

连接器 API 只用于账号管理。不要用它们为任务选择执行账号；`run_interactive_session()` 会处理任务期授权和账号选择。

可运行示例：

- [examples/auth/auth_example.py](examples/auth/auth_example.py)
- [examples/auth/connectors_example.py](examples/auth/connectors_example.py)

## Task Runner API

创建方式：

```python
runner = create_task_runner(ws_client, client, session_info)
```

主要方法：

- `run_interactive_session(initial_task, attachments=None, task_mode=TaskMode.Default, extra=None, options=None)`
- `run_task(task, attachments=None, task_mode=TaskMode.Default, extra=None, options=None) -> TaskResult`

营销任务优先使用 `run_interactive_session()`。非交互式 `run_task()` 在遇到授权、账号选择或浏览器插件连接需求时会安全失败。

常用选项：

- `verbose`：输出进度
- `auto_accept_plan`：自动批准 plan 消息
- `stop_on_x_confirm`：停止而不是确认社交动作
- `completion_timeout`：最大运行时间，单位秒

## 服务概览

- `client.session`：创建会话、停止会话、读取消息、读取营销数据
- `client.product`：创建产品分析任务、轮询状态、读取报告、读取分类
- `client.file_upload`：上传附件文件
- `client.user`：账户引导、API key、X 连接器管理
- `client.marketing`：营销看板 API
- `client.team`、`client.agent`、`client.browser`：辅助 API

## 错误类型

- `APIError`
- `NetworkError`
- `WebSocketError`
- `ConfigError`
- `SessionExecutionError`

## 文档

- 快速开始：[examples/quickstart_cn.md](examples/quickstart_cn.md)
- 安装说明：[installation_cn.md](installation_cn.md)
- 营销示例：[examples/getting_started/example.py](examples/getting_started/example.py)
- 产品分析示例：[examples/product_analysis/example.py](examples/product_analysis/example.py)
