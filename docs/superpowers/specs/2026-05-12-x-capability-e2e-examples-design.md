# X Capability E2E Examples 设计

## 背景

XAgent 能力决策文档定义了一个三维问题空间：

- 2 大运行环境：本地环境和远程环境
- 2 层执行能力：浏览器插件和 X API
- 4 类营销任务：回复、发布、互动和私信

SDK 当前在 `examples/getting_started` 中只有一个最小营销示例，但没有提供一个完整的 Live E2E runner 来验证所有能力决策路径。新的 example 项目将是一个小而聚焦的客户端：它会创建真实 session，通过 WebSocket 连接，运行 Agent，并验证矩阵中每个场景的预期结果。

这不是单元测试项目，也不是 dry-run 模拟器。它是一个真实的 E2E 验证客户端。

## 目标

- 在 `examples/x_capability_e2e/` 下新增一个 example 项目。
- 覆盖环境、执行能力、营销任务类型三者组合形成的全部 16 个场景。
- 通过现有 SDK 和 Agent 流程运行真实 marketing session。
- 允许真实 X 写操作，包括发布、互动和私信。
- 负向路径也必须创建真实 session，并检查 Agent 的拒绝或失败原因。
- 复用 `examples/getting_started` 中已有的 SDK 配置和 session runner 模式。
- 保持项目小、显式、易读。

## 非目标

- 不构建通用测试框架。
- 不引入 pytest 或其他测试 runner。
- 不增加 dry-run 模式。
- 不增加 `allow_write` 之类的写操作安全门。
- 不引入新的 SDK 或 Agent 协议字段。
- 不实现运行环境自动检测。
- 不并发运行场景。

## 项目结构

```text
examples/x_capability_e2e/
├── README.md
├── main.py
├── config.py
├── scenarios.py
├── runner.py
├── assertions.py
├── mate.yaml.example
└── results/
    └── .gitkeep
```

职责划分：

- `main.py`：CLI 入口、场景筛选、顺序执行、汇总输出。
- `config.py`：加载 `mate.yaml` 和 E2E 环境变量。
- `scenarios.py`：定义固定的 16 个场景及其预期结果。
- `runner.py`：创建 session，连接 WebSocket，运行 `TaskRunner.run_task()`，并收集 `TaskResult`。
- `assertions.py`：基于 `TaskResult` 的结构化字段分类为 pass、fail、timeout 或 error。
- `README.md`：说明配置方式，并明确提示该 runner 会执行真实 X 操作。
- `results/latest.json`：运行时生成，不提交。

## 配置

该 example 使用 `mate.yaml`，与 `examples/getting_started` 保持一致：

```yaml
mate:
  api_key: "your-api-key"
  # or jwt_token: "your-jwt-token"
  base_url: "https://api.dev.weclaw.ai"
  timeout: 30
```

额外 E2E 输入来自环境变量：

- `MATE_E2E_PRODUCT_ID`：可选的 marketing product ID。
- `MATE_E2E_TARGET_TWEET_URL`：回复和互动场景使用的 tweet URL。
- `MATE_E2E_TARGET_X_USER`：私信场景使用的 X username。
- `MATE_E2E_PUBLISH_TEXT_PREFIX`：发布场景使用的可选前缀。
- `MATE_E2E_TIMEOUT_SECONDS`：单场景超时时间，默认 `900`。
- `MATE_E2E_USER_INPUT_TIMEOUT_SECONDS`：意外输入请求的等待时间，默认 `120`。

Runner 不包含 `allow_write` 选项。运行该项目即表示用户接受真实 X 写操作。

`MATE_E2E_TIMEOUT_SECONDS` 必须同时注入到 `TaskExecutionOptions.completion_timeout` 和外层场景超时控制中。SDK 默认 `completion_timeout` 是 300 秒，如果不显式覆盖，外层 900 秒配置会失效。

## CLI

支持的命令：

```bash
python main.py --all
python main.py --scenario local-api-publish
python main.py --environment remote
python main.py --capability api
python main.py --task-type dm
```

筛选逻辑是简单的 AND 过滤。例如，`--environment remote --capability api` 只运行远程 API 场景。

## 场景模型

每个场景都是显式的数据对象，不是动态生成的 DSL：

```python
Scenario(
    id="local-api-publish",
    environment="local",
    capability="api",
    task_type="publish",
    expected="success",
)
```

字段含义：

- `environment`：`local` 或 `remote`。
- `capability`：`extension` 或 `api`。
- `task_type`：`reply`、`publish`、`interact` 或 `dm`。
- `expected`：`success` 或 `failure`。

能力映射：

- `capability=api` 映射为 `extra.execution_mode="api_only"`。
- `capability=extension` 映射为 `extra.execution_mode="extension_only"`。
- `environment=local` 映射为 `TaskExecutionOptions(browser_available=True)`。
- `environment=remote` 映射为 `TaskExecutionOptions(browser_available=False)`。

这会复用现有 SDK 和 Agent 行为，不新增协议字段。

`Scenario` 不保存 `execution_mode`、`browser_available` 或 `expected_path`：

- `execution_mode` 可由 `capability` 唯一推导。
- `browser_available` 可由 `environment` 唯一推导。
- 当前断言不消费 `expected_path`，因此不保留该字段。

场景模型只保留源矩阵中的核心变量，避免同一事实被重复声明。

## 场景矩阵

| Scenario | Expected | Reason |
| --- | --- | --- |
| `local-extension-reply` | success | 浏览器插件支持回复 |
| `local-extension-publish` | success | 插件可以发布，虽然 API 更可靠 |
| `local-extension-interact` | success | 插件完整支持互动 |
| `local-extension-dm` | failure | 插件不支持私信 |
| `local-api-reply` | failure | X API 不支持回复 |
| `local-api-publish` | success | X API 支持发布 |
| `local-api-interact` | success | X API 支持受限互动 |
| `local-api-dm` | success | X API 支持私信 |
| `remote-extension-reply` | failure | 远程环境没有浏览器插件 |
| `remote-extension-publish` | failure | 远程环境没有浏览器插件 |
| `remote-extension-interact` | failure | 远程环境没有浏览器插件 |
| `remote-extension-dm` | failure | 远程环境没有浏览器插件，且插件不能私信 |
| `remote-api-reply` | failure | X API 不支持回复 |
| `remote-api-publish` | success | X API 是远程发布的唯一路径 |
| `remote-api-interact` | success | X API 是远程互动的唯一路径，但能力受限 |
| `remote-api-dm` | success | X API 是远程私信的唯一路径 |

负向场景仍然必须创建真实 session，并等待 Agent 返回失败或拒绝原因。

## 任务提示词

每个场景使用固定提示词模板。每个场景都会包含一个 run ID 和随机后缀，便于追踪真实 X 操作，同时降低 X 平台重复内容或高频相似内容触发风控的概率：

```text
Run ID: 20260512-153000-local-api-publish
Nonce: k7p9q2

Use the configured X account to publish one short test tweet.
The tweet must include this exact run id and nonce: 20260512-153000-local-api-publish k7p9q2.
Do not ask for additional confirmation unless the system requires authorization.
```

任务类型：

- `reply`：回复 `MATE_E2E_TARGET_TWEET_URL`。
- `publish`：发布一条包含 run ID 的短测试 tweet。
- `interact`：与 `MATE_E2E_TARGET_TWEET_URL` 互动，例如 like 或 retweet。
- `dm`：向 `MATE_E2E_TARGET_X_USER` 发送一条包含 run ID 的私信。

提示词应直接、确定，不让模型自行选择任务类型。

为降低真实 X 写操作导致的误报：

- 每个场景生成不同 nonce，并写入发布、回复、私信正文。
- 发布文本包含 `MATE_E2E_PUBLISH_TEXT_PREFIX`、run ID、nonce 和简短随机短语。
- 同一轮矩阵中不复用完全相同的写入文本。
- 针对 X API rate limit、重复内容、spam detection 等明确平台拒绝，runner 将记录为 `ERROR`，不把它误判为能力矩阵失败。
- Runner 不做复杂重试；最多只允许对短暂网络错误做一次立即重试。真实平台风控拒绝不重试。

## 执行流程

对每个被选中的场景：

1. 构造任务提示词。
2. 构造包含默认 marketing skills 和 `execution_mode` 的 `extra`。
3. 当设置了 `MATE_E2E_PRODUCT_ID` 时，写入 `marketing_product.product_id`。
4. 使用 `CreateSessionRequest` 创建 marketing session。
5. 获取 `session_info`。
6. 创建 `WebSocketClient`。
7. 创建 `TaskRunner`。
8. 使用 `TaskExecutionOptions` 运行 `run_task()`。
9. 从返回的 `TaskResult` 读取 `success`、`final_answer`、`error`、`execution_logs`、`session_duration` 和 `message_count`。
10. 对 `TaskResult` 进行分类。
11. 存储结果并继续下一个场景。

场景顺序执行。这样真实 X 账号状态和 OAuth 交互更容易理解和排查。

`TaskExecutionOptions` 必须显式设置：

```python
TaskExecutionOptions(
    verbose=False,
    auto_accept_plan=True,
    browser_available=derive_browser_available(scenario.environment),
    completion_timeout=config.timeout_seconds,
    max_user_input_timeout=config.user_input_timeout_seconds,
    enable_event_logging=True,
)
```

其中：

- `config.timeout_seconds` 来自 `MATE_E2E_TIMEOUT_SECONDS`。
- `config.user_input_timeout_seconds` 来自 `MATE_E2E_USER_INPUT_TIMEOUT_SECONDS`。

`max_user_input_timeout` 必须是有限值，避免无人值守环境中因为授权或意外输入请求永久挂死。

## 授权处理

Live E2E runner 使用 `run_task()`，不使用 `run_interactive_session()`。原因是 `run_interactive_session()` 内部依赖 Python 原生 `input()`，在 CI/CD 或无人值守环境中遇到授权或意外输入请求时会永久阻塞。

授权策略：

- E2E 前置条件是 API 场景所需的 X connector 已完成授权。
- 如果运行中仍触发 `x_api_authorize` 或其他输入请求，runner 不进入阻塞式人工交互。
- `TaskExecutionOptions.max_user_input_timeout` 必须设置为有限值，使该场景按 `ERROR` 或 `TIMEOUT` 结束。
- 该结果说明 E2E 环境未预授权，不是能力矩阵本身失败。

需要人工验证 OAuth 恢复链路时，应单独运行 `examples/getting_started` 或另建手动授权检查，而不是混入这个自动化 E2E runner。

## 结果采集

Runner 不重定向 stdout/stderr，也不通过控制台文案做黑盒断言。执行证据来自 `TaskRunner.run_task()` 返回的 `TaskResult`：

每个场景结果记录：

- `scenario_id`
- `session_id`
- `environment`
- `capability`
- `task_type`
- `execution_mode`
- `browser_available`
- `expected`
- `status`
- `matched_reason`
- `task_success`
- `task_error`
- `final_answer`
- `message_count`
- `started_at`
- `ended_at`
- `duration_seconds`
- `exception`

## 断言

断言基于 `TaskResult`，不依赖 stdout/stderr 文案。

失败原因 marker：

```python
FAILURE_REASON_MARKERS = {
    "api_reply_unsupported": ["API", "reply", "not support"],
    "extension_dm_unsupported": ["extension", "direct message", "not support"],
    "extension_unavailable": ["browser", "extension", "unavailable"],
}
```

通过规则：

- 预期成功：`TaskResult.success is True`，`TaskResult.error is None`，且 `final_answer` 中没有匹配到拒绝原因。
- 预期失败：`final_answer` / `error` 中必须包含该场景对应的预期拒绝原因。单纯的 `TaskResult.success is False` 不足以通过，因为网络错误、平台风控和授权缺失也可能导致 `success=False`。
- 授权缺失：`error` 或 `execution_logs` 中出现 `x_api_authorize`、`authorization`、`connector` 等授权相关证据时，记录为 `ERROR`，提示先完成 X connector 预授权。
- 平台风控：`error` 或 `final_answer` 中出现 rate limit、duplicate、spam、policy 等 X 平台拒绝证据时，记录为 `ERROR`，避免误判为 Agent 能力决策错误。

Runner 不调用模型来判断输出。

## 错误处理

- 单个场景异常记录为 `ERROR`，不停止完整运行。
- 超时记录为 `TIMEOUT`。
- 断言不匹配记录为 `FAIL`。
- `KeyboardInterrupt` 停止运行，并写入部分结果。
- 任意非 pass 状态会让进程退出码为 `1`。
- 全部 pass 时进程退出码为 `0`。

## 控制台输出

汇总示例：

```text
X Capability E2E Summary

PASS  local-extension-reply     expected=success  session=sess_...
PASS  local-api-reply           expected=failure  reason=api_reply_unsupported
FAIL  remote-api-publish        expected=success  actual=timeout
ERROR local-api-dm              APIError: ...
```

## JSON 输出

运行结果写入 `examples/x_capability_e2e/results/latest.json`：

```json
{
  "run_id": "20260512-153000",
  "started_at": "2026-05-12T15:30:00+08:00",
  "ended_at": "2026-05-12T16:10:00+08:00",
  "summary": {
    "passed": 14,
    "failed": 1,
    "errors": 1,
    "timeouts": 0
  },
  "results": [
    {
      "scenario_id": "local-api-publish",
      "session_id": "sess_...",
      "expected": "success",
      "status": "PASS",
      "matched_reason": null,
      "task_success": true,
      "task_error": null,
      "message_count": 42,
      "duration_seconds": 123.4
    }
  ]
}
```

## Review Notes

该设计刻意选择显式数据和简单控制流，而不是可扩展性。场景集合是固定的，因为源决策文档定义的是固定的 16 路径矩阵。未来只有当源决策矩阵变化时，才应更新这个 example。
