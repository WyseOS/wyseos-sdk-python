# X Capability E2E Examples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `examples/x_capability_e2e/` 新增一个真实 Live E2E 客户端，顺序执行 X 能力决策矩阵中的 16 个场景，并用 `TaskResult` 结构化结果生成简洁摘要报告。

**Architecture:** 新 example 项目保持小型分层：`scenarios.py` 定义固定矩阵，`config.py` 读取配置，`runner.py` 负责真实 SDK session 执行，`assertions.py` 做结构化判定，`main.py` 负责 CLI 编排与结果落盘。Runner 使用 `TaskRunner.run_task()`，不使用阻塞式 `run_interactive_session()`，不重定向 stdout/stderr，不新增 SDK/Agent 协议字段。

**Tech Stack:** Python 3.9+ 标准库、现有 `octoevo.mate` SDK、Pydantic SDK models、WebSocketClient、TaskRunner。

---

## 文件结构

创建：

- `examples/x_capability_e2e/README.md`：运行说明、真实 X 写操作提示、配置示例。
- `examples/x_capability_e2e/main.py`：CLI 入口、场景筛选、顺序执行、汇总输出、退出码。
- `examples/x_capability_e2e/config.py`：加载 `mate.yaml` 和 E2E 环境变量。
- `examples/x_capability_e2e/scenarios.py`：固定 16 个场景、能力推导、任务提示词生成。
- `examples/x_capability_e2e/runner.py`：创建 session、WebSocket、TaskRunner，执行 `run_task()`。
- `examples/x_capability_e2e/assertions.py`：根据 `TaskResult` 判定 PASS/FAIL/ERROR/TIMEOUT。
- `examples/x_capability_e2e/mate.yaml.example`：配置模板。
- `examples/x_capability_e2e/results/.gitkeep`：保留结果目录。

不修改：

- `octoevo/mate/task_runner.py`
- `octoevo/mate/models.py`
- `examples/getting_started/example.py`

运行时生成，不提交：

- `examples/x_capability_e2e/results/latest.json`
- `examples/x_capability_e2e/results/latest.log`

## 实现约束

- 不新增单元测试文件，遵守仓库 `AGENTS.md`。
- 不引入 pytest 或测试框架。
- 不增加 dry-run、allow-write、并发执行、环境自动检测。
- 不做复杂 retry；仅允许 runner 对短暂网络异常做一次立即重试。
- `latest.json` 只保存摘要字段；`TaskResult.final_answer`、`error`、`execution_logs`、异常堆栈写入 `latest.log`。
- 代码中的注释和日志使用简短英文。

---

### Task 1: 创建项目骨架与配置读取

**Files:**
- Create: `examples/x_capability_e2e/config.py`
- Create: `examples/x_capability_e2e/mate.yaml.example`
- Create: `examples/x_capability_e2e/results/.gitkeep`

- [ ] **Step 1: 创建目录和占位文件**

创建目录：

```text
examples/x_capability_e2e/
examples/x_capability_e2e/results/
```

创建空文件：

```text
examples/x_capability_e2e/results/.gitkeep
```

- [ ] **Step 2: 编写 `mate.yaml.example`**

文件内容：

```yaml
mate:
  api_key: ""
  # jwt_token: ""
  base_url: "https://api.dev.weclaw.ai"
  timeout: 30
```

- [ ] **Step 3: 编写 `config.py`**

实现内容：

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from octoevo.mate import Client
from octoevo.mate.config import load_config


DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_USER_INPUT_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class E2EConfig:
    client: Client
    product_id: Optional[str]
    target_tweet_url: Optional[str]
    target_x_user: Optional[str]
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
        target_x_user=os.getenv("MATE_E2E_TARGET_X_USER", "").strip() or None,
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
python3 -m compileall examples/x_capability_e2e/config.py
```

Expected:

```text
Compiling 'examples/x_capability_e2e/config.py'...
```

- [ ] **Step 5: 提交**

```bash
git add examples/x_capability_e2e/config.py examples/x_capability_e2e/mate.yaml.example examples/x_capability_e2e/results/.gitkeep
git commit -m "feat: add x capability e2e config"
```

---

### Task 2: 定义固定 16 场景与提示词生成

**Files:**
- Create: `examples/x_capability_e2e/scenarios.py`

- [ ] **Step 1: 编写 `scenarios.py` 数据模型和矩阵**

实现内容：

```python
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal, Optional

Environment = Literal["local", "remote"]
Capability = Literal["extension", "api"]
TaskType = Literal["reply", "publish", "interact", "dm"]
Expected = Literal["success", "failure"]


@dataclass(frozen=True)
class Scenario:
    id: str
    environment: Environment
    capability: Capability
    task_type: TaskType
    expected: Expected
    expected_reason: Optional[str] = None


SCENARIOS = [
    Scenario("local-extension-reply", "local", "extension", "reply", "success"),
    Scenario("local-extension-publish", "local", "extension", "publish", "success"),
    Scenario("local-extension-interact", "local", "extension", "interact", "success"),
    Scenario("local-extension-dm", "local", "extension", "dm", "failure", "extension_dm_unsupported"),
    Scenario("local-api-reply", "local", "api", "reply", "failure", "api_reply_unsupported"),
    Scenario("local-api-publish", "local", "api", "publish", "success"),
    Scenario("local-api-interact", "local", "api", "interact", "success"),
    Scenario("local-api-dm", "local", "api", "dm", "success"),
    Scenario("remote-extension-reply", "remote", "extension", "reply", "failure", "extension_unavailable"),
    Scenario("remote-extension-publish", "remote", "extension", "publish", "failure", "extension_unavailable"),
    Scenario("remote-extension-interact", "remote", "extension", "interact", "failure", "extension_unavailable"),
    Scenario("remote-extension-dm", "remote", "extension", "dm", "failure", "extension_unavailable"),
    Scenario("remote-api-reply", "remote", "api", "reply", "failure", "api_reply_unsupported"),
    Scenario("remote-api-publish", "remote", "api", "publish", "success"),
    Scenario("remote-api-interact", "remote", "api", "interact", "success"),
    Scenario("remote-api-dm", "remote", "api", "dm", "success"),
]


def execution_mode_for(capability: Capability) -> str:
    return "api_only" if capability == "api" else "extension_only"


def browser_available_for(environment: Environment) -> bool:
    return environment == "local"


def make_run_id(run_prefix: str, scenario: Scenario) -> str:
    return f"{run_prefix}-{scenario.id}"


def make_nonce() -> str:
    return secrets.token_hex(3)


def default_run_prefix() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def filter_scenarios(
    scenario_id: Optional[str],
    environment: Optional[str],
    capability: Optional[str],
    task_type: Optional[str],
) -> list[Scenario]:
    selected: Iterable[Scenario] = SCENARIOS
    if scenario_id:
        selected = [s for s in selected if s.id == scenario_id]
    if environment:
        selected = [s for s in selected if s.environment == environment]
    if capability:
        selected = [s for s in selected if s.capability == capability]
    if task_type:
        selected = [s for s in selected if s.task_type == task_type]
    return list(selected)
```

- [ ] **Step 2: 追加提示词生成函数**

在同一文件末尾追加：

```python
def build_task_prompt(
    scenario: Scenario,
    run_id: str,
    nonce: str,
    publish_text_prefix: str,
    target_tweet_url: Optional[str],
    target_x_user: Optional[str],
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
    if scenario.task_type == "interact":
        if not target_tweet_url:
            raise ValueError("MATE_E2E_TARGET_TWEET_URL is required for interact scenarios")
        return (
            f"{header}\n"
            f"Use the configured X account to interact with this tweet: {target_tweet_url}\n"
            "Perform one available interaction such as like or retweet."
        )
    if scenario.task_type == "dm":
        if not target_x_user:
            raise ValueError("MATE_E2E_TARGET_X_USER is required for dm scenarios")
        return (
            f"{header}\n"
            f"Use the configured X account to send a direct message to @{target_x_user.lstrip('@')}.\n"
            f"The message must include this exact run id and nonce: {marker}."
        )
    raise ValueError(f"Unsupported task type: {scenario.task_type}")
```

- [ ] **Step 3: 运行语法检查和场景数量 smoke**

Run:

```bash
python3 -m compileall examples/x_capability_e2e/scenarios.py
python3 - <<'PY'
from examples.x_capability_e2e.scenarios import SCENARIOS
assert len(SCENARIOS) == 16
assert len({s.id for s in SCENARIOS}) == 16
print("scenarios ok")
PY
```

Expected:

```text
scenarios ok
```

- [ ] **Step 4: 提交**

```bash
git add examples/x_capability_e2e/scenarios.py
git commit -m "feat: add x capability e2e scenarios"
```

---

### Task 3: 实现结构化断言与报告模型

**Files:**
- Create: `examples/x_capability_e2e/assertions.py`

- [ ] **Step 1: 编写断言模型与 marker**

实现内容：

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from octoevo.mate.task_runner import TaskResult

from scenarios import Scenario

Status = Literal["PASS", "FAIL", "ERROR", "TIMEOUT"]

FAILURE_REASON_MARKERS = {
    "api_reply_unsupported": ["api", "reply", "not support"],
    "extension_dm_unsupported": ["extension", "direct message", "not support"],
    "extension_unavailable": ["browser", "extension", "unavailable"],
}

PLATFORM_ERROR_MARKERS = [
    "rate limit",
    "duplicate",
    "spam",
    "policy",
]

AUTH_ERROR_MARKERS = [
    "x_api_authorize",
    "authorization",
    "connector",
]


@dataclass(frozen=True)
class AssertionResult:
    status: Status
    matched_reason: Optional[str] = None
    message: str = ""


def _combined_text(result: TaskResult) -> str:
    parts = [result.final_answer or "", result.error or ""]
    for log in result.execution_logs:
        parts.append(str(log))
    return "\n".join(parts).lower()


def _contains_all(text: str, markers: list[str]) -> bool:
    return all(marker in text for marker in markers)
```

- [ ] **Step 2: 编写 `classify_result()`**

追加：

```python
def classify_result(scenario: Scenario, result: TaskResult) -> AssertionResult:
    text = _combined_text(result)
    if result.error and "timeout" in result.error.lower():
        return AssertionResult("TIMEOUT", message=result.error)

    if any(marker in text for marker in PLATFORM_ERROR_MARKERS):
        return AssertionResult("ERROR", "platform_rejected", "X platform rejected the action")

    if any(marker in text for marker in AUTH_ERROR_MARKERS):
        return AssertionResult("ERROR", "authorization_required", "X connector authorization is required")

    if scenario.expected == "failure":
        if scenario.expected_reason and _contains_all(text, FAILURE_REASON_MARKERS[scenario.expected_reason]):
            return AssertionResult("PASS", scenario.expected_reason)
        return AssertionResult("FAIL", scenario.expected_reason, "Expected rejection reason was not found")

    if not result.success:
        for reason, markers in FAILURE_REASON_MARKERS.items():
            if _contains_all(text, markers):
                return AssertionResult("FAIL", reason, "Unexpected rejection reason was found")

    if result.success and not result.error:
        return AssertionResult("PASS")
    return AssertionResult("FAIL", message=result.error or "Task did not succeed")
```

- [ ] **Step 3: 运行语法检查**

Run:

```bash
python3 -m compileall examples/x_capability_e2e/assertions.py
```

Expected:

```text
Compiling 'examples/x_capability_e2e/assertions.py'...
```

- [ ] **Step 4: 提交**

```bash
git add examples/x_capability_e2e/assertions.py
git commit -m "feat: add x capability e2e assertions"
```

---

### Task 4: 实现 Live E2E Runner

**Files:**
- Create: `examples/x_capability_e2e/runner.py`

- [ ] **Step 1: 编写 runner 数据模型和默认 marketing skills**

实现内容：

```python
from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from octoevo.mate import create_task_runner
from octoevo.mate.models import CreateSessionRequest
from octoevo.mate.task_runner import TaskExecutionOptions, TaskMode, TaskResult
from octoevo.mate.websocket import WebSocketClient

from assertions import AssertionResult, classify_result
from config import E2EConfig
from scenarios import (
    Scenario,
    browser_available_for,
    build_task_prompt,
    execution_mode_for,
    make_nonce,
    make_run_id,
)

DEFAULT_MARKETING_SKILLS = [
    {
        "skill_id": "7ccfb3d7-e6ac-4cda-bce3-030768ef9a9",
        "skill_name": "persona",
    }
]


@dataclass
class ScenarioRunResult:
    scenario_id: str
    session_id: Optional[str]
    environment: str
    capability: str
    task_type: str
    execution_mode: str
    browser_available: bool
    expected: str
    status: str
    matched_reason: Optional[str]
    started_at: str
    ended_at: str
    duration_seconds: float
```

- [ ] **Step 2: 编写 `to_json()` 和日志写入 helper**

追加：

```python
    def to_json(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "session_id": self.session_id,
            "environment": self.environment,
            "capability": self.capability,
            "task_type": self.task_type,
            "execution_mode": self.execution_mode,
            "browser_available": self.browser_available,
            "expected": self.expected,
            "status": self.status,
            "matched_reason": self.matched_reason,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _append_log(log_path: Path, title: str, content: str) -> None:
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {title}\n")
        f.write(content.rstrip())
        f.write("\n")
```

- [ ] **Step 3: 编写 `run_scenario()` 的 session 创建和执行逻辑**

追加：

```python
def _build_extra(config: E2EConfig, execution_mode: str) -> Dict[str, Any]:
    extra: Dict[str, Any] = {
        "skills": DEFAULT_MARKETING_SKILLS,
        "execution_mode": execution_mode,
    }
    if config.product_id:
        extra["marketing_product"] = {"product_id": config.product_id}
    return extra


def run_scenario(
    config: E2EConfig,
    scenario: Scenario,
    run_prefix: str,
    log_path: Path,
) -> ScenarioRunResult:
    started = _now()
    session_id: Optional[str] = None
    execution_mode = execution_mode_for(scenario.capability)
    browser_available = browser_available_for(scenario.environment)
    nonce = make_nonce()
    run_id = make_run_id(run_prefix, scenario)
    try:
        task = build_task_prompt(
            scenario=scenario,
            run_id=run_id,
            nonce=nonce,
            publish_text_prefix=config.publish_text_prefix,
            target_tweet_url=config.target_tweet_url,
            target_x_user=config.target_x_user,
        )
        extra = _build_extra(config, execution_mode)
        req = CreateSessionRequest(
            task=task,
            mode=TaskMode.Marketing.value,
            platform="api",
            extra=extra,
        )
        session = config.client.session.create(req)
        session_id = session.session_id
        session_info = config.client.session.get_info(session.session_id)
        ws_client = WebSocketClient(
            base_url=config.client.base_url,
            api_key=config.client.api_key or "",
            jwt_token=config.client.jwt_token or "",
            session_id=session_info.session_id,
            heartbeat_interval=30,
        )
        task_runner = create_task_runner(ws_client, config.client, session_info)
        result = task_runner.run_task(
            task=task,
            task_mode=TaskMode.Marketing,
            extra=extra,
            options=TaskExecutionOptions(
                auto_accept_plan=True,
                verbose=False,
                completion_timeout=config.timeout_seconds,
                max_user_input_timeout=config.user_input_timeout_seconds,
                browser_available=browser_available,
                enable_event_logging=True,
            ),
        )
        assertion = classify_result(scenario, result)
        _write_task_log(log_path, scenario, session_id, result, assertion)
    except Exception as exc:
        result = None
        assertion = AssertionResult("ERROR", message=str(exc))
        _append_log(log_path, scenario.id, traceback.format_exc())

    ended = _now()
    return ScenarioRunResult(
        scenario_id=scenario.id,
        session_id=session_id,
        environment=scenario.environment,
        capability=scenario.capability,
        task_type=scenario.task_type,
        execution_mode=execution_mode,
        browser_available=browser_available,
        expected=scenario.expected,
        status=assertion.status,
        matched_reason=assertion.matched_reason,
        started_at=_iso(started),
        ended_at=_iso(ended),
        duration_seconds=(ended - started).total_seconds(),
    )
```

- [ ] **Step 4: 编写 `_write_task_log()`**

在 `run_scenario()` 前追加：

```python
def _write_task_log(
    log_path: Path,
    scenario: Scenario,
    session_id: Optional[str],
    result: TaskResult,
    assertion: AssertionResult,
) -> None:
    content = "\n".join(
        [
            f"scenario_id={scenario.id}",
            f"session_id={session_id or ''}",
            f"status={assertion.status}",
            f"matched_reason={assertion.matched_reason or ''}",
            f"message={assertion.message}",
            "",
            "[error]",
            result.error or "",
            "",
            "[final_answer]",
            result.final_answer or "",
            "",
            "[execution_logs]",
            "\n".join(str(log) for log in result.execution_logs),
        ]
    )
    _append_log(log_path, scenario.id, content)
```

- [ ] **Step 5: 运行语法检查**

Run:

```bash
python3 -m compileall examples/x_capability_e2e/runner.py
```

Expected:

```text
Compiling 'examples/x_capability_e2e/runner.py'...
```

- [ ] **Step 6: 提交**

```bash
git add examples/x_capability_e2e/runner.py
git commit -m "feat: add x capability e2e runner"
```

---

### Task 5: 实现 CLI 编排、报告输出和 README

**Files:**
- Create: `examples/x_capability_e2e/main.py`
- Create: `examples/x_capability_e2e/README.md`

- [ ] **Step 1: 编写 `main.py` imports、参数解析和 summary helper**

实现内容：

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import load_e2e_config
from runner import ScenarioRunResult, run_scenario
from scenarios import default_run_prefix, filter_scenarios


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run X capability Live E2E scenarios.")
    parser.add_argument("--all", action="store_true", help="Run all scenarios.")
    parser.add_argument("--scenario", help="Run one scenario by id.")
    parser.add_argument("--environment", choices=["local", "remote"])
    parser.add_argument("--capability", choices=["extension", "api"])
    parser.add_argument("--task-type", choices=["reply", "publish", "interact", "dm"])
    return parser


def _summary(results: list[ScenarioRunResult]) -> dict[str, int]:
    return {
        "passed": sum(1 for r in results if r.status == "PASS"),
        "failed": sum(1 for r in results if r.status == "FAIL"),
        "errors": sum(1 for r in results if r.status == "ERROR"),
        "timeouts": sum(1 for r in results if r.status == "TIMEOUT"),
    }
```

- [ ] **Step 2: 编写报告写入和控制台输出**

追加：

```python
def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_summary(results: list[ScenarioRunResult]) -> None:
    print("\nX Capability E2E Summary\n")
    for result in results:
        reason = f" reason={result.matched_reason}" if result.matched_reason else ""
        session = f" session={result.session_id}" if result.session_id else ""
        print(f"{result.status:<7} {result.scenario_id:<28} expected={result.expected}{reason}{session}")
```

- [ ] **Step 3: 编写 `main()`**

追加：

```python
def main() -> int:
    base_dir = Path(__file__).resolve().parent
    args = _build_parser().parse_args()
    if not args.all and not any([args.scenario, args.environment, args.capability, args.task_type]):
        print("Specify --all or at least one filter.", file=sys.stderr)
        return 2

    config = load_e2e_config(base_dir)
    scenarios = filter_scenarios(
        scenario_id=args.scenario,
        environment=args.environment,
        capability=args.capability,
        task_type=args.task_type,
    )
    if not scenarios:
        print("No scenarios matched.", file=sys.stderr)
        return 2

    config.result_dir.mkdir(parents=True, exist_ok=True)
    log_path = config.result_dir / "latest.log"
    log_path.write_text("", encoding="utf-8")

    started_at = _now_iso()
    run_prefix = default_run_prefix()
    results: list[ScenarioRunResult] = []
    try:
        for scenario in scenarios:
            print(f"\nRunning {scenario.id}...")
            result = run_scenario(config, scenario, run_prefix, log_path)
            results.append(result)
            print(f"{result.status} {result.scenario_id}")
    except KeyboardInterrupt:
        print("\nInterrupted. Writing partial results.")

    ended_at = _now_iso()
    payload = {
        "run_id": run_prefix,
        "started_at": started_at,
        "ended_at": ended_at,
        "summary": _summary(results),
        "results": [r.to_json() for r in results],
    }
    _write_json(config.result_dir / "latest.json", payload)
    _print_summary(results)
    return 0 if results and all(r.status == "PASS" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 编写 `README.md`**

内容：

```markdown
# X Capability E2E

This example runs real Live E2E marketing sessions for the X capability matrix.

It performs real X actions. Publishing, replying, interacting, and direct messages may be sent by the configured account.

## Setup

```bash
cp mate.yaml.example mate.yaml
```

Configure `mate.yaml` with `api_key` or `jwt_token`.

Optional environment variables:

```bash
export MATE_E2E_PRODUCT_ID=""
export MATE_E2E_TARGET_TWEET_URL="https://x.com/.../status/..."
export MATE_E2E_TARGET_X_USER="target_user"
export MATE_E2E_PUBLISH_TEXT_PREFIX="Wyse E2E test"
export MATE_E2E_TIMEOUT_SECONDS=900
export MATE_E2E_USER_INPUT_TIMEOUT_SECONDS=120
```

API scenarios require a pre-authorized X connector. This runner does not handle interactive OAuth.

## Run

```bash
python main.py --all
python main.py --scenario local-api-publish
python main.py --environment remote --capability api
python main.py --task-type dm
```

Results:

- `results/latest.json`: summary report
- `results/latest.log`: debug details
```

- [ ] **Step 5: 运行语法检查和 CLI smoke**

Run:

```bash
python3 -m compileall examples/x_capability_e2e
python3 examples/x_capability_e2e/main.py
```

Expected:

```text
Specify --all or at least one filter.
```

Exit code should be `2`.

- [ ] **Step 6: 提交**

```bash
git add examples/x_capability_e2e/main.py examples/x_capability_e2e/README.md
git commit -m "feat: add x capability e2e cli"
```

---

### Task 6: 最终验证与收尾

**Files:**
- Verify only.

- [ ] **Step 1: 运行全项目 example 编译**

Run:

```bash
python3 -m compileall examples/x_capability_e2e
```

Expected: all files compile without traceback.

- [ ] **Step 2: 运行非网络 smoke**

Run:

```bash
python3 - <<'PY'
from examples.x_capability_e2e.scenarios import SCENARIOS, filter_scenarios

assert len(SCENARIOS) == 16
assert len(filter_scenarios(None, "remote", "api", None)) == 4
assert len(filter_scenarios("local-api-publish", None, None, None)) == 1
print("smoke ok")
PY
```

Expected:

```text
smoke ok
```

- [ ] **Step 3: 检查报告字段没有中间态冗余**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

needles = ("task_success", "task_error", "message_count")
root = Path("examples/x_capability_e2e")
matches = []
for path in root.rglob("*"):
    if path.is_file() and path.suffix in {".py", ".md", ".json"}:
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                matches.append(f"{path}: {needle}")
if matches:
    raise SystemExit("\n".join(matches))
print("summary fields ok")
PY
```

Expected:

```text
summary fields ok
```

- [ ] **Step 4: 可选 Live 单场景验证**

仅在本地已配置 `mate.yaml` 且确认真实 X 写操作可接受时运行：

```bash
python3 examples/x_capability_e2e/main.py --scenario remote-api-reply
```

Expected: creates a real session, writes `results/latest.json` and `results/latest.log`, and returns PASS only if the Agent returns the expected API reply unsupported reason.

- [ ] **Step 5: 检查 git 状态**

Run:

```bash
git status --short
```

Expected: only intended files are modified or untracked before final commit.

- [ ] **Step 6: 如 Task 6 有修正，提交**

```bash
git add examples/x_capability_e2e
git commit -m "fix: polish x capability e2e example"
```

If Task 6 made no file changes, skip this commit.

---

## 自审

- Spec 覆盖：16 场景、`run_task()`、结构化断言、timeout 注入、非阻塞授权策略、摘要 JSON + 调试 log、run ID + nonce、防平台风控误判，均有对应任务。
- 占位检查：计划中无未完成占位符。
- 类型一致性：`Scenario` 保留矩阵字段和静态 `expected_reason`；`execution_mode` 和 `browser_available` 在 runner 中推导；JSON 不包含 `task_success`、`task_error`、`message_count`。
- 项目约束：不新增单元测试文件，不引入 pytest，不修改 SDK 源码。
