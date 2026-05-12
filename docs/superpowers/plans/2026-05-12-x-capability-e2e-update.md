# X Capability E2E Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收缩 `examples/x_capability_e2e` 为 12 条 SDK 侧自动矩阵，改用稳定 reason code 断言，并把 Agent 运行态检查下沉到 README 手动 smoke。

**Architecture:** 保持 `examples/x_capability_e2e` 作为一个小型分层 runner，不改 SDK 核心。`scenarios.py` 与 `config.py` 先完成范围收缩，`assertions.py` 重写为结构化 reason code 判定，`main.py` / `runner.py` 只做必要对齐，最后用精简 README 承载手动 smoke 命令。

**Tech Stack:** Python 3.9+、现有 `octoevo.mate` SDK、`TaskRunner.run_task()`、`compileall`、`rg`

---

## 文件结构

修改：

- `examples/x_capability_e2e/scenarios.py`
  - 责任：删除 `dm`，把矩阵收缩为 12 场景，保留 `reply / publish / interact`
- `examples/x_capability_e2e/config.py`
  - 责任：删除 `target_x_user`，恢复超时环境变量读取
- `examples/x_capability_e2e/assertions.py`
  - 责任：移除自然语言 marker，改为 reason code 优先的结构化断言
- `examples/x_capability_e2e/main.py`
  - 责任：去掉 `dm` CLI 入口，保持顺序执行与摘要输出
- `examples/x_capability_e2e/runner.py`
  - 责任：删除与 `dm` 收缩冲突的调用点，保持 JSON 摘要精简
- `examples/x_capability_e2e/README.md`
  - 责任：把自动覆盖更新为 12 场景，并追加手动 smoke

不修改：

- `octoevo/mate/*`
- `examples/getting_started/*`
- 任何测试文件
- Agent 仓库代码

## 实现约束

- 不新增单元测试，遵守仓库 `AGENTS.md`
- 不新增 `auto` 执行模式
- 不做 extension bootstrap
- 不新增 runner 选项或全局状态
- 日志和注释保持简短英文
- `latest.json` 继续只保存摘要字段

### Task 1: 收缩场景矩阵与配置模型

**Files:**
- Modify: `examples/x_capability_e2e/scenarios.py`
- Modify: `examples/x_capability_e2e/config.py`

- [ ] **Step 1: 修改 `scenarios.py` 的任务类型与场景矩阵**

将类型与矩阵收缩到 12 场景：

```python
Environment = Literal["local", "remote"]
Capability = Literal["extension", "api"]
TaskType = Literal["reply", "publish", "interact"]
Expected = Literal["success", "failure"]


SCENARIOS = [
    Scenario("local-extension-reply", "local", "extension", "reply", "success"),
    Scenario("local-extension-publish", "local", "extension", "publish", "success"),
    Scenario("local-extension-interact", "local", "extension", "interact", "success"),
    Scenario("local-api-reply", "local", "api", "reply", "failure", "REPLY_API_UNSUPPORTED"),
    Scenario("local-api-publish", "local", "api", "publish", "success"),
    Scenario("local-api-interact", "local", "api", "interact", "success"),
    Scenario("remote-extension-reply", "remote", "extension", "reply", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-extension-publish", "remote", "extension", "publish", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-extension-interact", "remote", "extension", "interact", "failure", "EXTENSION_REQUIRED"),
    Scenario("remote-api-reply", "remote", "api", "reply", "failure", "REPLY_API_UNSUPPORTED"),
    Scenario("remote-api-publish", "remote", "api", "publish", "success"),
    Scenario("remote-api-interact", "remote", "api", "interact", "success"),
]
```

- [ ] **Step 2: 删除 `build_task_prompt()` 里的 `dm` 分支**

把函数收口为 3 类任务，删除 `target_x_user` 参数：

```python
def build_task_prompt(
    scenario: Scenario,
    run_id: str,
    nonce: str,
    publish_text_prefix: str,
    target_tweet_url: Optional[str],
) -> str:
    marker = f"{run_id} {nonce}"
    header = (
        f"Run ID: {run_id}\n"
        f"Nonce: {nonce}\n\n"
        "Do not ask for additional confirmation unless the system requires authorization.\n"
    )
    if scenario.task_type == "reply":
        if not target_tweet_url:
            raise ValueError("MATE_E2E_TARGET_TWEET_URL is required for reply scenarios")
        return (
            f"{header}\n"
            f"Use the configured X account to reply to this tweet: {target_tweet_url}\n"
            f"The reply must include this exact run id and nonce: {marker}."
        )
    if scenario.task_type == "publish":
        return (
            f"{header}\n"
            "Use the configured X account to publish one short test tweet.\n"
            f"The tweet text must include: {publish_text_prefix} {marker}."
        )
    if not target_tweet_url:
        raise ValueError("MATE_E2E_TARGET_TWEET_URL is required for interact scenarios")
    return (
        f"{header}\n"
        f"Use the configured X account to interact with this tweet: {target_tweet_url}\n"
        "Perform one available interaction such as like or retweet."
    )
```

- [ ] **Step 3: 修改 `config.py`，删掉 `target_x_user` 并恢复超时环境变量**

将配置模型改成：

```python
@dataclass(frozen=True)
class E2EConfig:
    client: Client
    product_id: Optional[str]
    target_tweet_url: Optional[str]
    publish_text_prefix: str
    timeout_seconds: int
    user_input_timeout_seconds: int
    result_dir: Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value


def load_e2e_config(base_dir: Path) -> E2EConfig:
    config_path = base_dir / "mate.yaml"
    client = Client(load_config(str(config_path)))
    return E2EConfig(
        client=client,
        product_id=os.getenv("MATE_E2E_PRODUCT_ID", "").strip() or None,
        target_tweet_url=os.getenv("MATE_E2E_TARGET_TWEET_URL", "").strip() or None,
        publish_text_prefix=os.getenv("MATE_E2E_PUBLISH_TEXT_PREFIX", "Wyse E2E test").strip()
        or "Wyse E2E test",
        timeout_seconds=_env_int("MATE_E2E_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        user_input_timeout_seconds=_env_int(
            "MATE_E2E_USER_INPUT_TIMEOUT_SECONDS",
            DEFAULT_USER_INPUT_TIMEOUT_SECONDS,
        ),
        result_dir=base_dir / "results",
    )
```

- [ ] **Step 4: 运行语法检查**

Run:

```bash
python3 -m compileall examples/x_capability_e2e/scenarios.py examples/x_capability_e2e/config.py
```

Expected:

```text
Compiling 'examples/x_capability_e2e/scenarios.py'...
Compiling 'examples/x_capability_e2e/config.py'...
```

- [ ] **Step 5: 扫描 `dm` 残留**

Run:

```bash
rg -n "\bdm\b|target_x_user" examples/x_capability_e2e/scenarios.py examples/x_capability_e2e/config.py
```

Expected:

```text
No matches
```

- [ ] **Step 6: 提交**

```bash
git add examples/x_capability_e2e/scenarios.py examples/x_capability_e2e/config.py
git commit -m "refactor: shrink x capability e2e matrix"
```

### Task 2: 重写断言为 reason code 优先

**Files:**
- Modify: `examples/x_capability_e2e/assertions.py`

- [ ] **Step 1: 增加 execution log 解析 helper**

用最小 helper 从 `TaskResult.execution_logs` 中提取可匹配文本：

```python
def _text_parts(result: TaskResult) -> list[str]:
    parts = [result.final_answer or "", result.error or ""]
    for log in result.execution_logs:
        parts.append(str(log))
        metadata = getattr(log, "metadata", None) or {}
        parts.extend(str(value) for value in metadata.values())
    return [part for part in parts if part]


def _contains(text_parts: list[str], needle: str) -> bool:
    lowered = needle.lower()
    return any(lowered in part.lower() for part in text_parts)
```

- [ ] **Step 2: 用稳定 code 常量替换旧 marker**

将模块常量改成：

```python
EXPECTED_FAILURE_CODES = {
    "REPLY_API_UNSUPPORTED",
    "EXTENSION_REQUIRED",
}
ENVIRONMENT_ERROR_CODES = {
    "ACCOUNT_IDENTIFIER_REQUIRED",
}
AUTH_ERROR_MARKERS = {
    "x_api_authorize",
    "AUTH_REQUIRED",
    "TOKEN_EXPIRED",
    "INSUFFICIENT_SCOPE",
}
PLATFORM_ERROR_MARKERS = {
    "rate limit",
    "duplicate",
    "spam",
    "policy",
}
```

- [ ] **Step 3: 重写 `classify_result()`**

使用结构化顺序：

```python
def classify_result(scenario: Scenario, result: TaskResult) -> AssertionResult:
    parts = _text_parts(result)

    if result.error and "timeout" in result.error.lower():
        return AssertionResult("TIMEOUT", message=result.error)

    if any(_contains(parts, marker) for marker in PLATFORM_ERROR_MARKERS):
        return AssertionResult("ERROR", "platform_rejected", "Platform rejected the action")

    if any(_contains(parts, code) for code in ENVIRONMENT_ERROR_CODES):
        return AssertionResult("ERROR", "ACCOUNT_IDENTIFIER_REQUIRED", "Missing X account identity")

    if any(_contains(parts, marker) for marker in AUTH_ERROR_MARKERS):
        return AssertionResult("ERROR", "authorization_required", "Authorization is required")

    if scenario.expected == "failure":
        if scenario.expected_reason and _contains(parts, scenario.expected_reason):
            return AssertionResult("PASS", scenario.expected_reason)
        return AssertionResult("FAIL", scenario.expected_reason, "Expected failure reason was not observed")

    for code in EXPECTED_FAILURE_CODES:
        if _contains(parts, code):
            return AssertionResult("FAIL", code, "Unexpected capability rejection was observed")

    if result.success and not result.error:
        return AssertionResult("PASS")

    return AssertionResult("FAIL", message=result.error or "Task did not succeed")
```

- [ ] **Step 4: 删除旧的自然语言 marker 与无用 helper**

删除：

```python
FAILURE_REASON_MARKERS = ...
PLATFORM_ERROR_MARKERS = ["rate limit", "duplicate", "spam", "policy"]
AUTH_ERROR_MARKERS = ["x_api_authorize", "authorization"]

def _combined_text(...):
...

def _contains_all(...):
...
```

保留 `AssertionResult` 和 `Status` 定义不变。

- [ ] **Step 5: 运行语法检查**

Run:

```bash
python3 -m compileall examples/x_capability_e2e/assertions.py
```

Expected:

```text
Compiling 'examples/x_capability_e2e/assertions.py'...
```

- [ ] **Step 6: 扫描旧断言残留**

Run:

```bash
rg -n "not support|authorization\"|connector|extension_dm_unsupported|api_reply_unsupported|extension_unavailable" examples/x_capability_e2e/assertions.py
```

Expected:

```text
No matches
```

- [ ] **Step 7: 提交**

```bash
git add examples/x_capability_e2e/assertions.py
git commit -m "refactor: use reason code assertions for x capability e2e"
```

### Task 3: 对齐 runner 与 CLI

**Files:**
- Modify: `examples/x_capability_e2e/runner.py`
- Modify: `examples/x_capability_e2e/main.py`

- [ ] **Step 1: 从 `runner.py` 删除 `dm` 相关调用**

更新 `build_task_prompt()` 调用，只传保留参数：

```python
task = build_task_prompt(
    scenario=scenario,
    run_id=run_id,
    nonce=nonce,
    publish_text_prefix=config.publish_text_prefix,
    target_tweet_url=config.target_tweet_url,
)
```

保留以下 options 注入不变：

```python
options=TaskExecutionOptions(
    auto_accept_plan=True,
    verbose=False,
    completion_timeout=config.timeout_seconds,
    max_user_input_timeout=config.user_input_timeout_seconds,
    browser_available=browser_available,
    enable_event_logging=True,
)
```

- [ ] **Step 2: 保持 JSON 摘要最小，不新增衍生字段**

确认 `ScenarioRunResult.to_json()` 仍只输出：

```python
return {
    "scenario_id": self.scenario_id,
    "session_id": self.session_id,
    "environment": self.environment,
    "capability": self.capability,
    "task_type": self.task_type,
    "expected": self.expected,
    "status": self.status,
    "matched_reason": self.matched_reason,
    "started_at": _iso(self.started_at),
    "ended_at": _iso(self.ended_at),
    "duration_seconds": self.duration_seconds,
}
```

不要把 `execution_mode`、`browser_available` 重新放回 JSON。

- [ ] **Step 3: 更新 `main.py` 的 `--task-type` 选项**

将 CLI 参数改成：

```python
parser.add_argument("--task-type", choices=("reply", "publish", "interact"))
```

其余筛选逻辑保持不变。

- [ ] **Step 4: 运行语法检查**

Run:

```bash
python3 -m compileall examples/x_capability_e2e/main.py examples/x_capability_e2e/runner.py
```

Expected:

```text
Compiling 'examples/x_capability_e2e/main.py'...
Compiling 'examples/x_capability_e2e/runner.py'...
```

- [ ] **Step 5: 运行轻量 CLI smoke**

Run:

```bash
python3 examples/x_capability_e2e/main.py
```

Expected:

```text
Specify --all or at least one filter.
```

Exit code should be `2`.

- [ ] **Step 6: 扫描 `dm` CLI 残留**

Run:

```bash
rg -n "\bdm\b|target_x_user" examples/x_capability_e2e/main.py examples/x_capability_e2e/runner.py
```

Expected:

```text
No matches
```

- [ ] **Step 7: 提交**

```bash
git add examples/x_capability_e2e/main.py examples/x_capability_e2e/runner.py
git commit -m "refactor: align x capability e2e runner"
```

### Task 4: 更新 README 与手动 smoke

**Files:**
- Modify: `examples/x_capability_e2e/README.md`

- [ ] **Step 1: 收缩 README 的自动矩阵说明**

将开头和运行说明改成精简版本：

```md
# X Capability E2E

This directory runs real Live E2E marketing sessions for the X capability matrix.

The automatic runner covers 12 SDK-side scenarios:

- `local/remote`
- `api/extension`
- `reply/publish/interact`

It does not cover `dm` or `auto` mode.
```

并把环境变量示例改成：

```bash
export MATE_E2E_PRODUCT_ID="product-id"
export MATE_E2E_TARGET_TWEET_URL="https://x.com/user/status/123"
export MATE_E2E_PUBLISH_TEXT_PREFIX="Wyse E2E test"
export MATE_E2E_TIMEOUT_SECONDS="900"
export MATE_E2E_USER_INPUT_TIMEOUT_SECONDS="120"
```

- [ ] **Step 2: 删除 `dm` 和 16 场景相关段落**

将运行命令收口为：

```md
## Run

```bash
python main.py --all
python main.py --capability extension
python main.py --environment remote
python main.py --task-type reply
python main.py --scenario local-api-publish
```
```

不要再保留：

- `All 16 Scenarios`
- `Direct Message Flows`
- `MATE_E2E_TARGET_X_USER`

- [ ] **Step 3: 追加 `Manual smoke` 段落**

在 README 末尾追加精简命令与观察点：

```md
## Manual smoke

These checks are not covered by the automatic SDK runner. Run them from the agent repository.

1. `api_only + reply=10`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --task "只处理当前会话中的待回复推文"
```
Expected: no entry guard; reply returns `REPLY_API_UNSUPPORTED`; pending replies remain.

2. `api_only + interact=5, draft=10 + missing identity`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only
```
Expected: `ACCOUNT_IDENTIFIER_REQUIRED` with precise user-facing wording.

3. `api_only + interact=5, draft=10 + ready identity + authorized credential`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --x-account <x_username_or_id>
```
Expected: normal X API execution.

4. `auto + extension disconnected + reply=10`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode auto
```
Expected: `EXTENSION_REQUIRED`.

5. `auto + extension connected + draft=10`, then close the extension once
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode auto --x-account <x_username_or_id> --task "只发布当前会话中的待发布推文草稿"
```
Expected: plan A exits cleanly and plan B takes over.

6. `extension_only + extension connected + reply=10 + partial failures`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode extension_only
```
Expected: user-facing failures are not misclassified as extension-required.

7. `extension_only + extension disconnected`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode extension_only
```
Expected: cmd fails fast.

8. `api_only` popup suppression
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --x-account <x_username_or_id>
```
Expected: no popup creation log and no `TASK_STARTED_DEFAULT`.
```

- [ ] **Step 4: 扫描 README 残留**

Run:

```bash
rg -n "dm|16 Scenarios|target_x_user|Direct Message|MATE_E2E_TARGET_X_USER" examples/x_capability_e2e/README.md
```

Expected:

```text
No matches
```

- [ ] **Step 5: 运行格式检查**

Run:

```bash
git diff --check -- examples/x_capability_e2e/README.md
```

Expected:

```text
No output
```

- [ ] **Step 6: 提交**

```bash
git add examples/x_capability_e2e/README.md
git commit -m "docs: update x capability e2e readme"
```

### Task 5: 最终一致性验证

**Files:**
- Verify only: `examples/x_capability_e2e/*`

- [ ] **Step 1: 运行全量语法检查**

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m compileall examples/x_capability_e2e
```

Expected:

```text
Compiling 'examples/x_capability_e2e/assertions.py'...
Compiling 'examples/x_capability_e2e/config.py'...
Compiling 'examples/x_capability_e2e/main.py'...
Compiling 'examples/x_capability_e2e/runner.py'...
Compiling 'examples/x_capability_e2e/scenarios.py'...
```

- [ ] **Step 2: 扫描自动矩阵边界残留**

Run:

```bash
rg -n "\bdm\b|target_x_user|All 16|16 Scenarios|extension_dm_unsupported|api_reply_unsupported|extension_unavailable" examples/x_capability_e2e
```

Expected:

```text
No matches
```

- [ ] **Step 3: 扫描 reason code 是否对齐**

Run:

```bash
rg -n "REPLY_API_UNSUPPORTED|EXTENSION_REQUIRED|ACCOUNT_IDENTIFIER_REQUIRED|x_api_authorize" examples/x_capability_e2e
```

Expected:

```text
Matches in scenarios.py, assertions.py, and README.md only
```

- [ ] **Step 4: 查看最终 diff**

Run:

```bash
git diff -- examples/x_capability_e2e
```

Expected:

```text
Only the six planned files are modified, with no unrelated churn
```

- [ ] **Step 5: 提交最终整理**

如果前面任务之间有额外修正，补一个最终提交：

```bash
git add examples/x_capability_e2e
git commit -m "refactor: update x capability e2e coverage"
```

若没有额外修正且工作区已干净，此步跳过。

## 自审

### Spec coverage

本计划覆盖了 spec 中的全部要求：

- 自动矩阵收缩为 12 场景：Task 1
- 删除 `dm`：Task 1、Task 3、Task 4、Task 5
- 断言改为 reason code 优先：Task 2
- `ACCOUNT_IDENTIFIER_REQUIRED` / 授权缺失归为 `ERROR`：Task 2
- `README` 增加手动 smoke：Task 4
- 不改 SDK 核心、不加测试框架：体现在文件范围和实现约束中

### Placeholder scan

已检查：

- 无 `TODO` / `TBD`
- 无“类似 Task N”式跳转
- 每个代码修改步骤都给出了实际代码
- 每个验证步骤都给出了精确命令和预期

### Type consistency

已统一：

- `TaskType` 只保留 `reply / publish / interact`
- `expected_reason` 使用 `REPLY_API_UNSUPPORTED` / `EXTENSION_REQUIRED`
- `E2EConfig` 不再包含 `target_x_user`
- `build_task_prompt()` 与 `run_scenario()` 的参数签名一致
