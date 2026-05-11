# X Execution Mode SDK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 agent 端以自包含 INPUT 事件发出 `x_api_authorize`，并让 Python SDK 在远程安全默认行为下完成 X connector 授权 URL 输出、目标账号防呆和 API-only 示例补齐。

**Architecture:** 方案分两层：agent 端先修正事件契约，让 `x_api_authorize` payload 直接进入 `UserInputRequestedEvent` 对应的 WebSocket INPUT data；SDK 端只识别 `message.message.data.type == "x_api_authorize"` 这一唯一入口。SDK 不做跨事件暂存，不引入全局状态，浏览器打开能力统一收口到 `TaskExecutionOptions.browser_available`。

**Tech Stack:** Python, Pydantic, WebSocket JSON protocol, existing `TaskRunner`, existing `UserService.authorize_x_account()`, Autogen `UserInputRequestedEvent`

---

## 文件结构

### Agent 端

- Modify: `/Users/eric/git/AI/wyse/wysemate_agent/src/wyse_mate_agent/agents/approval_guard.py`
  - 责任：让 `interact()` 支持把结构化 input payload 挂到 `UserInputRequestedEvent.metadata` 上。
- Modify: `/Users/eric/git/AI/wyse/wysemate_agent/src/wyse_mate_agent/helper/mate_helper.py`
  - 责任：把 `UserInputRequestedEvent.metadata["data"]` 合并进 WebSocket INPUT 事件的 `message.data`，并清理内部 metadata。
- Modify: `/Users/eric/git/AI/wyse/wysemate_agent/src/wyse_mate_agent/agents/web_browser/x_browser/x_web_browser.py`
  - 责任：发出精简后的 `x_api_authorize` payload，只包含 `type`、`external_user_id`、`external_username`、`reason_code`。

### SDK 端

- Modify: `octoevo/mate/task_runner.py`
  - 责任：新增 `TaskExecutionOptions.browser_available`；统一 URL 输出/打开逻辑；处理自包含 `x_api_authorize` INPUT；目标账号 connector 匹配；恢复提示；空回车继续。
- Modify: `examples/getting_started/example.py`
  - 责任：展示 API-only marketing execution mode 的最小用法。
- Modify: `examples/quickstart.md`
  - 责任：补充 API-only execution mode 和授权 URL 行为说明。
- Modify: `examples/quickstart_cn.md`
  - 责任：补充中文 API-only execution mode 和授权 URL 行为说明。

## 实施约束

- 不新增单元测试文件。
- 不新增 `_pending_x_api_authorize_payload` 或任何跨事件暂存逻辑。
- 不新增模块级 `could_use_browser` 或类似全局状态。
- 不新增 `TaskRunner.set_browser_available()`。
- SDK 只识别 `message.message.data.get("type") == "x_api_authorize"`。
- `x_api_authorize` payload 不包含 `session_id`、`execution_mode`、`reason_message`。
- Go 后端 connector API 不改。
- 每个 task 完成后按本计划提交一次，提交前只 stage 本 task 明确列出的文件。

---

### Task 1: 修正 agent 端 INPUT 事件协议

**Files:**
- Modify: `/Users/eric/git/AI/wyse/wysemate_agent/src/wyse_mate_agent/agents/approval_guard.py`
- Modify: `/Users/eric/git/AI/wyse/wysemate_agent/src/wyse_mate_agent/helper/mate_helper.py`
- Modify: `/Users/eric/git/AI/wyse/wysemate_agent/src/wyse_mate_agent/agents/web_browser/x_browser/x_web_browser.py`

- [ ] **Step 1: 修改 `BaseInterActiveGuard.interact` 类型签名**

在 `approval_guard.py` 顶部确认已导入 `Any`。如果当前 import 没有 `Any`，将 typing import 调整为包含 `Any`：

```python
from typing import Any, AsyncGenerator, Protocol, Union
```

把 `BaseInterActiveGuard` protocol 中的 `interact` 签名改为：

```python
def interact(
    self,
    source: str,
    action_description: TextMessage | MultiModalMessage,
    cancellation_token: CancellationToken,
    data_type: str | None = None,
    send_description: bool = False,
    input_type: str = "text",
    input_data: dict[str, Any] | None = None,
) -> AsyncGenerator[Union[Any, str], None]: ...
```

- [ ] **Step 2: 修改 `ApprovalGuard.interact` 方法签名**

在同一文件中，把具体实现的 `interact()` 签名改为：

```python
async def interact(
    self,
    source: str,
    action_description: TextMessage | MultiModalMessage,
    cancellation_token: CancellationToken,
    data_type: str | None = None,
    send_description: bool = False,
    input_type: str = "text",
    input_data: dict[str, Any] | None = None,
) -> AsyncGenerator[Union[Any, str], None]:
```

- [ ] **Step 3: 让 `UserInputRequestedEvent` 携带 input metadata**

在 `ApprovalGuard.interact()` 中，替换当前这行：

```python
yield UserInputRequestedEvent(request_id=request_id, source=source)
```

替换为：

```python
input_metadata: dict[str, Any] = {"input_type": input_type}
if input_data is not None:
    input_metadata["data"] = input_data
event = UserInputRequestedEvent(request_id=request_id, source=source)
event.metadata = input_metadata
yield event
```

说明：这里不改变普通 text input 的行为，默认仍是 `input_type="text"`，且没有额外 data。

- [ ] **Step 4: 修改 `mate_helper.py` 的 UserInputRequestedEvent 转换逻辑**

在 `mate_helper.py` 的 `_format_message()` 中，找到：

```python
elif isinstance(message, UserInputRequestedEvent):
    content = message.content
    _input_type = (getattr(message, "metadata", None) or {}).get("input_type", "text")
    message_data = {"type": _input_type, "data": {"request_id": message.request_id}}
    # Clear metadata — input_type is internal, not for frontend
    message.metadata = {}
```

替换为：

```python
elif isinstance(message, UserInputRequestedEvent):
    content = message.content
    input_metadata = getattr(message, "metadata", None) or {}
    _input_type = input_metadata.get("input_type", "text")
    event_data = {"request_id": message.request_id}
    extra_data = input_metadata.get("data")
    if isinstance(extra_data, dict):
        event_data.update(extra_data)
    message_data = {"type": _input_type, "data": event_data}
    # Clear internal routing metadata after materializing the INPUT payload.
    message.metadata = {}
```

验收标准：`input_type="x_api_authorize"` 且 `input_data={"type": "x_api_authorize", "external_user_id": "123", "external_username": "wyse", "reason_code": "TOKEN_EXPIRED"}` 时，WebSocket INPUT 事件的 `message.data.type` 必须是 `x_api_authorize`。

- [ ] **Step 5: 修改 `x_web_browser.py` 的授权 payload**

在 `_emit_x_api_authorize_interaction()` 中，将当前 payload 改为只保留必要字段：

```python
payload = {
    "type": "x_api_authorize",
    "external_user_id": external_user_id,
    "external_username": external_username,
    "reason_code": result.reason_code,
}
```

删除 payload 中的 `session_id`、`execution_mode`、`reason_message`。

- [ ] **Step 6: 让 `x_api_authorize` 走自包含 INPUT，同时保留人类可读描述**

在 `_emit_x_api_authorize_interaction()` 中，`description` 继续作为普通 `TextMessage` 发出，保证旧版 SDK 或第三方客户端至少能看到“需要 X OAuth2 授权”的人类可读说明。同时通过 `input_type` / `input_data` 让新版 SDK 从随后的 INPUT 事件中读取结构化 payload。将调用改为：

```python
async for item in self._interactive_guard.interact(
    source=self.name,
    action_description=description,
    cancellation_token=CancellationToken(),
    data_type="x_api_authorize",
    send_description=True,
    input_type="x_api_authorize",
    input_data=payload,
):
    yield item
```

验收标准：agent 会先发一条普通 TEXT 描述消息，供旧客户端展示；随后发出的 INPUT 事件必须自包含 `x_api_authorize` payload。新版 SDK 只消费 INPUT payload，不解析前一条 TEXT。

- [ ] **Step 7: 编译检查 agent 修改文件**

Run:

```bash
cd /Users/eric/git/AI/wyse/wysemate_agent
uv run python -m compileall \
  src/wyse_mate_agent/agents/approval_guard.py \
  src/wyse_mate_agent/helper/mate_helper.py \
  src/wyse_mate_agent/agents/web_browser/x_browser/x_web_browser.py
```

Expected:

```text
Compiling 'src/wyse_mate_agent/agents/approval_guard.py'...
Compiling 'src/wyse_mate_agent/helper/mate_helper.py'...
Compiling 'src/wyse_mate_agent/agents/web_browser/x_browser/x_web_browser.py'...
```

如果某个文件已由 Python 缓存判断为最新，`compileall` 可能不打印该文件名；退出码为 `0` 即通过。

- [ ] **Step 8: 提交 agent 协议修正**

Run:

```bash
cd /Users/eric/git/AI/wyse/wysemate_agent
git add \
  src/wyse_mate_agent/agents/approval_guard.py \
  src/wyse_mate_agent/helper/mate_helper.py \
  src/wyse_mate_agent/agents/web_browser/x_browser/x_web_browser.py
git commit -m "fix: make x api authorize input self contained"
```

---

### Task 2: SDK 增加声明式浏览器可用性和统一 URL 行为

**Files:**
- Modify: `octoevo/mate/task_runner.py`

- [ ] **Step 1: 给 `TaskExecutionOptions` 增加 `browser_available`**

在 `TaskExecutionOptions` 中，放在 `stop_on_x_confirm` 后面：

```python
    browser_available: bool = False  # Opt-in: local browser can be opened safely
```

保留已有字段，不新增 setter，不新增全局变量。

- [ ] **Step 2: 替换 `_open_url` 为返回 bool 的安全 helper**

把当前 `_open_url()` 替换为：

```python
def _normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def _open_url(url: str) -> bool:
    try:
        webbrowser.open(_normalize_url(url), new=2)
        return True
    except Exception as exc:
        logger.warning("Failed to open URL in browser: %s", exc)
        return False
```

- [ ] **Step 3: 新增统一 URL 输出 helper**

在 `_open_url()` 后新增：

```python
def _show_or_open_url(url: str, options: TaskExecutionOptions, label: str) -> None:
    normalized = _normalize_url(url)
    if options.browser_available and _open_url(normalized):
        print(f"{label}: opened in browser")
        return
    print(f"{label}:")
    print(normalized)
```

说明：默认只打印 URL；只有 `browser_available=True` 且打开成功才不重复打印 URL。

- [ ] **Step 4: 让 `x_confirm` 使用统一 URL helper**

在 `_handle_input_message()` 的 `inner_type == "x_confirm"` 分支中，替换：

```python
open_url = self._extension_url_for_x_confirm()
if open_url:
    try:
        _open_url(open_url)
    except Exception as e:
        logger.warning(
            "Failed to open browser before x_confirm (url=%s): %s",
            open_url,
            e,
        )
```

替换为：

```python
open_url = self._extension_url_for_x_confirm()
if open_url:
    _show_or_open_url(open_url, options, "Open this URL to connect the browser extension")
```

保留后续 `create_x_confirm_response()` 和自动确认逻辑不变。

- [ ] **Step 5: 编译检查 SDK**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
python -m compileall octoevo/mate/task_runner.py
```

Expected:

```text
Compiling 'octoevo/mate/task_runner.py'...
```

- [ ] **Step 6: 提交浏览器行为收口**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
git add octoevo/mate/task_runner.py
git commit -m "feat: make sdk browser opening opt in"
```

---

### Task 3: SDK 处理自包含 `x_api_authorize` INPUT

**Files:**
- Modify: `octoevo/mate/task_runner.py`

- [ ] **Step 1: 增加 x_api_authorize payload 识别 helper**

在 `_extension_url_for_x_confirm()` 后新增：

```python
    def _get_x_api_authorize_payload(self, message: Dict) -> Optional[Dict[str, Any]]:
        msg_inner = message.get("message", {})
        if isinstance(msg_inner, str):
            return None
        message_data = msg_inner.get("data", {})
        if not isinstance(message_data, dict):
            return None
        if message_data.get("type") != "x_api_authorize":
            return None
        return message_data
```

验收标准：这里只认 `message.message.data.type`，不读 metadata，不解析 TEXT content。

- [ ] **Step 2: 增加 connector 匹配 helper**

在同一类中新增：

```python
    def _find_target_x_connector_id(
        self,
        external_user_id: Optional[str],
        external_username: Optional[str],
    ) -> Optional[str]:
        accounts = self.client.user.list_x_accounts().items
        if external_user_id:
            for account in accounts:
                if account.external_user_id == external_user_id:
                    return account.connector_id
        if external_username:
            normalized = external_username.lstrip("@")
            for account in accounts:
                if account.external_username.lstrip("@") == normalized:
                    return account.connector_id
        return None
```

- [ ] **Step 3: 增加未命中目标账号 warning helper**

新增：

```python
    def _warn_x_authorize_target_unverified(
        self,
        external_user_id: Optional[str],
        external_username: Optional[str],
    ) -> None:
        if external_username or external_user_id:
            handle = f"@{external_username.lstrip('@')}" if external_username else "(unknown handle)"
            print(
                "WARNING: Agent 要求执行任务的 X 账号为 "
                f"{handle}（external_user_id={external_user_id or 'unknown'}）。"
            )
            print("请确保接下来打开的网页中登录并授权的是这个账号，否则当前任务将无法继续。")
            return
        print("WARNING: Agent 未提供目标 X 账号标识，请确认接下来授权的 X 账号正确。")
```

- [ ] **Step 4: 增加 x_api_authorize handler**

新增：

```python
    def _handle_x_api_authorize_message(
        self,
        payload: Dict[str, Any],
        options: TaskExecutionOptions,
        timestamp: str,
    ) -> None:
        request_id = payload.get("request_id")
        external_user_id = payload.get("external_user_id")
        external_username = payload.get("external_username")
        reason_code = payload.get("reason_code")

        target_connector_id = None
        try:
            target_connector_id = self._find_target_x_connector_id(
                external_user_id=external_user_id,
                external_username=external_username,
            )
        except Exception as exc:
            logger.warning("Failed to list X connector accounts: %s", exc)
            print("WARNING: 无法列出现有 X connector，SDK 不能校验目标账号。请确认接下来授权的 X 账号正确。")

        if target_connector_id is None:
            self._warn_x_authorize_target_unverified(external_user_id, external_username)

        try:
            resp = self.client.user.authorize_x_account(
                target_connector_id=target_connector_id,
            )
        except Exception as exc:
            logger.error("Failed to create X authorization URL: %s", exc)
            print(f"X authorization failed: {exc}")
            if options.event_logging_enabled:
                self._log_event("error", f"x_api_authorize failed: {exc}", timestamp)
            return

        _show_or_open_url(resp.auth_url, options, "Open this URL to authorize X API access")
        print("请在浏览器中完成授权后，回到此终端按回车键（或输入任意内容）以继续当前任务。")

        self._pending_request_id = request_id
        self._pending_input_type = InputType.TEXT
        self._pending_request_at = time.time()
        self._pending_empty_input_request_id = request_id
        if options.event_logging_enabled:
            self._log_event(
                "system",
                f"x_api_authorize url issued reason={reason_code or 'unknown'} target_connector_id={target_connector_id or 'new'}",
                timestamp,
            )
```

- [ ] **Step 5: 用 request_id 绑定空回车放行状态**

在 `TaskRunner.__init__` 中新增：

```python
        self._pending_empty_input_request_id: Optional[str] = None
```

不要在 timeout、x_confirm、plan accept 等分支中分散清理这个字段。空回车能否放行只由当前 pending request 决定：

```python
        self._pending_empty_input_request_id == self._pending_request_id
```

现有代码已经集中管理 `self._pending_request_id` 的生命周期；请求结束后 `_pending_request_id` 会被置空，因此旧的 `_pending_empty_input_request_id` 即使保留，也不会继续生效。这样避免在多个无关分支里手动撒清理逻辑。

- [ ] **Step 6: 在 `_handle_input_message()` 中优先处理 x_api_authorize**

在现有 `if not request_id: ... return` 之后立即加入：

```python
        x_api_authorize_payload = self._get_x_api_authorize_payload(message)
        if x_api_authorize_payload is not None:
            self._handle_x_api_authorize_message(
                x_api_authorize_payload,
                options,
                timestamp,
            )
            return
```

验收标准：`x_api_authorize` 不进入 x_confirm、plan auto-accept 或普通 input 分支。

- [ ] **Step 7: 让空回车可以继续 x_api_authorize**

在 `run_interactive_session()` 的用户输入循环中，找到：

```python
                    if not user_input:
                        print("→ Empty input ignored")
                        continue
```

替换为：

```python
                    if (
                        not user_input
                        and self._pending_empty_input_request_id != self._pending_request_id
                    ):
                        print("→ Empty input ignored")
                        continue
                    if (
                        not user_input
                        and self._pending_empty_input_request_id == self._pending_request_id
                    ):
                        user_input = "continue"
```

不需要在发送 input response 成功后手动清理 `_pending_empty_input_request_id`；发送成功后既有代码会清空 `_pending_request_id`，request_id 绑定自然失效。

- [ ] **Step 8: 编译检查 SDK**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
python -m compileall octoevo/mate/task_runner.py
```

Expected:

```text
Compiling 'octoevo/mate/task_runner.py'...
```

- [ ] **Step 9: 提交 x_api_authorize SDK handler**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
git add octoevo/mate/task_runner.py
git commit -m "feat: handle x api authorization input"
```

---

### Task 4: 补充 API-only 示例与 quickstart

**Files:**
- Modify: `examples/getting_started/example.py`
- Modify: `examples/quickstart.md`
- Modify: `examples/quickstart_cn.md`

- [ ] **Step 1: 更新 getting started 示例的 extra 构造**

在 `examples/getting_started/example.py` 中找到 `build_extra(product_id: str) -> Dict`。保持原有默认行为不变，新增可选环境变量控制：

```python
def build_extra(product_id: str) -> Dict:
    extra = {"skills": DEFAULT_MARKETING_SKILLS}
    execution_mode = os.getenv("MATE_X_EXECUTION_MODE", "").strip()
    if execution_mode:
        extra["execution_mode"] = execution_mode
    if product_id:
        extra["marketing_product"] = {"product_id": product_id}
    return extra
```

验收标准：默认不传 `execution_mode`；用户设置 `MATE_X_EXECUTION_MODE=api_only` 时透传。

- [ ] **Step 2: 在英文 quickstart 增加 API-only 片段**

在 `examples/quickstart.md` 的 marketing session 示例附近加入：

````markdown
For X API-only execution, pass `execution_mode` in `extra`:

```python
extra = {
    "execution_mode": "api_only",
    "marketing_product": {"product_id": "prod_123"},
}
```

When X OAuth authorization is required, the SDK prints an authorization URL by default. Open it in a browser, finish authorization, then return to the terminal and press Enter to continue.
````

- [ ] **Step 3: 在中文 quickstart 增加 API-only 片段**

在 `examples/quickstart_cn.md` 的 marketing session 示例附近加入：

````markdown
如果需要 X API-only 执行，在 `extra` 中传入 `execution_mode`：

```python
extra = {
    "execution_mode": "api_only",
    "marketing_product": {"product_id": "prod_123"},
}
```

当需要 X OAuth 授权时，SDK 默认只打印授权 URL。请在浏览器中打开该 URL 完成授权，然后回到终端按回车继续。
````

- [ ] **Step 4: 编译示例文件**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
python -m compileall examples/getting_started/example.py
```

Expected:

```text
Compiling 'examples/getting_started/example.py'...
```

- [ ] **Step 5: 提交示例和 quickstart**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
git add examples/getting_started/example.py examples/quickstart.md examples/quickstart_cn.md
git commit -m "docs: show x api only sdk usage"
```

---

### Task 5: 最终验证与回归检查

**Files:**
- 不预期修改源码文件。

- [ ] **Step 1: SDK 编译检查**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
python -m compileall octoevo/mate examples/getting_started/example.py
```

Expected:

```text
Listing 'octoevo/mate'...
```

退出码必须为 `0`。

- [ ] **Step 2: Agent 编译检查**

Run:

```bash
cd /Users/eric/git/AI/wyse/wysemate_agent
uv run python -m compileall \
  src/wyse_mate_agent/agents/approval_guard.py \
  src/wyse_mate_agent/helper/mate_helper.py \
  src/wyse_mate_agent/agents/web_browser/x_browser/x_web_browser.py
```

Expected: 退出码为 `0`。

- [ ] **Step 3: 静态检查协议中不应存在的字段**

Run:

```bash
cd /Users/eric/git/AI/wyse/wysemate_agent
rg -n '"session_id": self\\._session_id|"execution_mode": self\\._x_execution_mode|"reason_message": result\\.reason_message' \
  src/wyse_mate_agent/agents/web_browser/x_browser/x_web_browser.py
```

Expected: no matches.

- [ ] **Step 4: 静态检查 SDK 没有旧协议暂存**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
rg -n "_pending_x_api_authorize_payload|metadata\\.data_type|message\\.message\\.type|set_browser_available|could_use_browser" octoevo/mate
```

Expected: no matches.

说明：如果 `metadata.data_type` 出现在其它既有无关逻辑中，确认不是 `x_api_authorize` handler 后不要改动。

- [ ] **Step 5: 手工构造 SDK handler smoke**

在 Python REPL 或临时 scratch 命令中运行以下代码，不提交任何 scratch 文件：

```python
from types import SimpleNamespace
from octoevo.mate.task_runner import TaskExecutionOptions, TaskRunner

class DummyUser:
    def list_x_accounts(self):
        return SimpleNamespace(items=[
            SimpleNamespace(
                connector_id="conn_1",
                external_user_id="123",
                external_username="wyse",
            )
        ])

    def authorize_x_account(self, target_connector_id=None):
        assert target_connector_id == "conn_1"
        return SimpleNamespace(auth_url="https://auth.example/x")

class DummyClient:
    api_key = "test"
    user = DummyUser()

class DummyWS:
    pass

runner = TaskRunner(DummyWS(), DummyClient(), SimpleNamespace(session_id="sess_1"))
payload = {
    "type": "x_api_authorize",
    "request_id": "req_1",
    "external_user_id": "123",
    "external_username": "wyse",
    "reason_code": "TOKEN_EXPIRED",
}
runner._handle_x_api_authorize_message(payload, TaskExecutionOptions(), "now")
assert runner._pending_request_id == "req_1"
assert runner._pending_empty_input_request_id == "req_1"
```

Expected: 无 assertion error；终端打印授权 URL 和恢复提示。

- [ ] **Step 6: 检查 git 状态**

Run:

```bash
cd /Users/eric/git/AI/wyse/mate-sdk-python
git status --short
cd /Users/eric/git/AI/wyse/wysemate_agent
git status --short
```

Expected: only known pre-existing unrelated files may remain. No modified files from this implementation should be unstaged.

---

## 计划自查清单

- Spec 覆盖：
  - execution_mode 透传：Task 4 示例覆盖，SDK 协议主体不重复实现。
  - agent 自包含 INPUT：Task 1 覆盖。
  - SDK 唯一识别入口：Task 3 Step 1 和 Step 6 覆盖。
  - browser_available 声明式配置：Task 2 覆盖。
  - connector 匹配与未命中 warning：Task 3 Step 2 和 Step 3 覆盖。
  - 授权 URL 后恢复提示：Task 3 Step 4 和 Step 7 覆盖。
  - 不新增旧协议暂存：实施约束和 Task 5 Step 4 覆盖。
- 无新增单元测试文件；验证使用 compileall、静态检查和手工 smoke。
- 每个任务都有明确文件、命令、预期结果和提交点。
