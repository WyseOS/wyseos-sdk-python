# X Capability E2E 更新设计

## 背景

`examples/x_capability_e2e/` 当前已经存在一个可运行的 SDK 侧 Live E2E runner，但它仍然带有上一轮方案中的几类偏差：

- 覆盖范围仍按 16 场景设计，包含当前不在范围内的 `dm`
- 断言仍然依赖自然语言 marker，而不是 Agent 已稳定输出的 reason code
- 自动矩阵与 Agent 运行态 smoke 的边界不清晰，容易把 `auto`、pending 数量、popup 日志等问题误塞进 SDK runner
- README 既没有清晰声明自动覆盖边界，也没有把必须人工验证的问题收拢成可执行命令

与此同时，Agent 侧已经完成新的执行模式分发实现：

- `launch_x_browser.py` 区分 `auto / api_only / extension_only` 的连接失败语义
- `web_browser_gui.py` 将 extension session guard 抽成可覆写 hook
- `x_web_browser.py` 用稳定的 marketing turn 判断驱动 guard 和 dispatch，并把 marketing dispatch 前置到 popup 初始化之前
- `x_capability_decision_control.py` 统一了 `EXTENSION_REQUIRED` / `REPLY_API_UNSUPPORTED`
- `ACCOUNT_IDENTIFIER_REQUIRED` 已有精准文案，不再泛化成 `X API unavailable`

本次更新的目标，是让 `X Capability E2E` 与这些 Agent 新语义重新对齐，同时保持 examples 项目本身足够小、足够清楚。

## 目标

- 将 `X Capability E2E` 明确收敛为一个 SDK 侧自动矩阵 runner
- 自动覆盖只验证 SDK 侧可以稳定观察和断言的能力矩阵结果
- 从自动矩阵中移除当前不在范围内的 `dm`
- 断言逻辑改为优先匹配 `TaskResult.execution_logs` 中的稳定 reason code
- 把 `auto`、pending 数量、扩展中途断开、popup 创建日志、`TASK_STARTED_DEFAULT` 等运行态检查移出自动 runner
- 在 `README.md` 末尾补充精简的手动 smoke 命令，复用 Agent 侧现有入口

## 非目标

- 不修改 `octoevo/mate` 核心 SDK 代码
- 不修改 `examples/getting_started`
- 不为 `X Capability E2E` 增加新的测试框架、单元测试或 dry-run 模式
- 不在 SDK 仓库内新增 Agent smoke helper 脚本
- 不把 `auto` 模式硬塞进自动矩阵
- 不把数据库 pending 数量校验加入自动 runner
- 不把 Agent 内部 popup / task start 日志校验加入自动 runner
- 不实现本地 extension bootstrap token 生成逻辑

## 设计原则

- 自动矩阵只覆盖 SDK 侧稳定、结构化、可重复断言的内容
- 运行态、计数类、环境依赖强的检查，统一下沉为手动 smoke
- 断言只认稳定协议证据，不靠文案猜测
- 场景模型只保留源矩阵核心变量，不保存重复推导字段
- README 只补充必要命令，不扩写成运维手册

## 自动矩阵边界

### 保留的矩阵维度

- 环境：`local` / `remote`
- 能力：`extension` / `api`
- 任务：`reply` / `publish` / `interact`

### 移除的维度

- `dm`
- `auto`

原因：

- `dm` 当前不在本次 Agent 范围内
- `auto` 属于 Agent 运行态语义验证，不属于 SDK 自动矩阵的稳定职责

### 自动矩阵总数

自动 runner 最终只保留 12 个场景：

- `local-extension-reply`
- `local-extension-publish`
- `local-extension-interact`
- `local-api-reply`
- `local-api-publish`
- `local-api-interact`
- `remote-extension-reply`
- `remote-extension-publish`
- `remote-extension-interact`
- `remote-api-reply`
- `remote-api-publish`
- `remote-api-interact`

## 场景预期

### 成功场景

- `local-extension-reply`
- `local-extension-publish`
- `local-extension-interact`
- `local-api-publish`
- `local-api-interact`
- `remote-api-publish`
- `remote-api-interact`

这些场景的判定目标是：

- `TaskResult.success == True`
- 没有命中授权错误
- 没有命中平台拒绝
- 没有命中能力拒绝 reason code

### 预期失败场景

- `local-api-reply`
- `remote-api-reply`
  - `expected_reason = "REPLY_API_UNSUPPORTED"`

- `remote-extension-reply`
- `remote-extension-publish`
- `remote-extension-interact`
  - `expected_reason = "EXTENSION_REQUIRED"`

这些场景必须以稳定 reason code 为准，不再依赖自然语言 `not support`、`unavailable` 等文案。

### 非矩阵失败

以下情况不是矩阵通过条件，而是测试环境或运行环境问题，应归为 `ERROR`：

- `ACCOUNT_IDENTIFIER_REQUIRED`
- 触发 `x_api_authorize`
- 连接器未授权或授权失效
- X 平台 rate limit / duplicate / spam / policy 拒绝
- 本地 extension 场景运行时环境未准备好，导致无法进入预期路径

这样可以明确区分：

- 能力矩阵本身不支持
- 测试环境没有准备好

## 数据模型调整

### `Scenario`

`Scenario` 只保留以下字段：

- `id`
- `environment`
- `capability`
- `task_type`
- `expected`
- `expected_reason`

不保留：

- `execution_mode`
- `browser_available`
- `expected_path`

原因：

- `execution_mode` 可由 `capability` 唯一推导
- `browser_available` 可由 `environment` 唯一推导
- 当前自动断言不消费 `expected_path`

### `E2EConfig`

移除与 `dm` 绑定的 `target_x_user`。

保留：

- `product_id`
- `target_tweet_url`
- `publish_text_prefix`
- `timeout_seconds`
- `user_input_timeout_seconds`

并继续支持：

- `MATE_E2E_TIMEOUT_SECONDS`
- `MATE_E2E_USER_INPUT_TIMEOUT_SECONDS`

这两个配置必须注入 `TaskExecutionOptions`，不能回退到 SDK 默认超时。

## 断言设计

### 证据来源

自动 runner 只使用两类证据：

- `TaskResult.success / error / final_answer`
- `TaskResult.execution_logs`

其中 `execution_logs` 是能力拒绝和授权状态的主判断源。

### 主判断规则

#### `TIMEOUT`

当 `result.error` 明确包含 timeout 时，归类为 `TIMEOUT`。

#### `ERROR`

满足任一条件时归类为 `ERROR`：

- 命中 `ACCOUNT_IDENTIFIER_REQUIRED`
- 命中 `x_api_authorize` 或明确授权失败 reason
- 命中平台拒绝类错误：rate limit、duplicate、spam、policy
- 运行环境错误导致无法验证矩阵

#### `PASS`

满足任一条件时归类为 `PASS`：

- 成功场景执行成功，且没有命中 `ERROR`
- 失败场景命中其声明的 `expected_reason`

#### `FAIL`

满足任一条件时归类为 `FAIL`：

- 失败场景没有观察到其 `expected_reason`
- 成功场景命中了能力拒绝类 reason code
- 结果既不是成功，也不属于 `TIMEOUT` 或 `ERROR`

### 明确淘汰的旧逻辑

不再保留以下断言方式：

- 扫描 `authorization`、`connector` 之类高频通用词
- 用 `not support`、`unavailable` 这类文案片段猜测 reason
- 先扫整段自然语言日志，再决定是不是授权错误

## 自动 runner 的行为边界

### 保持不变的部分

- 继续使用 `run_task()`
- 继续顺序执行场景
- 继续输出 `latest.json` 和 `latest.log`
- 继续使用 `TaskExecutionOptions(browser_available=...)`

### 明确不做的部分

- 不新增 `auto` 执行模式
- 不实现 extension bootstrap
- 不尝试生成 Agent 本地专用的 `wyse_token`
- 不对 pending 记录数量做前后对比
- 不读取 Agent 进程日志判断 popup 或 `TASK_STARTED_DEFAULT`

原因：

- 这些能力属于 Agent 本地运行态验证，不是 SDK 自动矩阵 runner 的职责
- SDK 仓库没有提供稳定、公开、同层级的 extension bootstrap 接口
- 如果强行加入，会让 examples 项目膨胀成第二套 Agent 调试工具

## README 调整

`README.md` 需要做三类修改。

### 1. 收缩自动覆盖说明

- 从 16 场景改为 12 场景
- 删除全部 `dm` 描述
- 不再把 `auto` 写入自动 runner 范围

### 2. 保留最小运行说明

README 仍只保留：

- 配置 `mate.yaml`
- 配置环境变量
- 运行 `python main.py --all`
- 运行筛选命令
- 查看 `results/latest.json`
- 查看 `results/latest.log`

### 3. 追加 `Manual smoke`

在 README 末尾增加一个很短的 `Manual smoke` 段落。

这段内容只做两件事：

- 说明以下问题不由自动 runner 覆盖
- 给出 Agent 侧现有命令和观察点

命令只复用：

- `wysemate_agent/cmd/launch_x_browser.py`
- `wysemate_agent/cmd/test_x_api_agent.py`

不在 SDK 仓库新增新的 smoke helper。

## 手动 smoke 覆盖项

以下问题不进入自动矩阵，统一放入 README 的手动 smoke。

### 1. `api_only + reply=10`

目标：

- 确认 entry guard 不触发
- reply 返回 `REPLY_API_UNSUPPORTED`
- pending reply 不被错误消费

### 2. `api_only + interact=5, draft=10 + 无 extra identity`

目标：

- 确认 preflight 失败为 `ACCOUNT_IDENTIFIER_REQUIRED`
- 确认用户实际看到的是精准文案，而不是泛化的 `X API unavailable`

### 3. `api_only + interact=5, draft=10 + 完整 extra identity + 已授权`

目标：

- 确认正常进入 X API 执行

### 4. `auto + 扩展未连接 + reply=10`

目标：

- 确认返回 `EXTENSION_REQUIRED`

### 5. `auto + 扩展连接 + draft=10，中途手动关闭扩展`

目标：

- 确认 Plan A 能优雅退出并进入 Plan B
- 确认 per-record re-check 生效

### 6. `extension_only + 扩展连接 + reply=10 + 故意制造部分失败`

目标：

- 观察失败文案是否被错误归因为“需要插件”

### 7. `extension_only + 扩展未连接`

目标：

- 确认 `launch_x_browser.py` 启动期 fail-fast

### 8. `api_only`

目标：

- 确认不触发 popup 创建日志
- 确认不触发 `TASK_STARTED_DEFAULT`

这些检查都依赖以下至少一项：

- Agent 本地运行命令
- 预置 pending 数据
- 扩展连接或手动断开
- 运行时日志

因此不适合并入 SDK 自动矩阵。

## 文件修改范围

只修改：

- `examples/x_capability_e2e/scenarios.py`
- `examples/x_capability_e2e/config.py`
- `examples/x_capability_e2e/assertions.py`
- `examples/x_capability_e2e/runner.py`
- `examples/x_capability_e2e/main.py`
- `examples/x_capability_e2e/README.md`

不修改：

- `octoevo/mate/*`
- `examples/getting_started/*`
- Agent 仓库代码

## 风险与约束

### 本地 extension 成功场景的前提

`local-extension-*` 依赖运行者本地已有可用扩展环境。自动 runner 不负责生成 bootstrap token，也不负责启动 Agent 本地专用扩展链路。

因此：

- 若环境就绪，场景应成功
- 若环境未就绪，场景应明确落到 `ERROR` 或 `EXTENSION_REQUIRED`

这不是矩阵设计缺陷，而是自动 runner 的职责边界

### 授权链路不是自动 runner 的通过条件

自动 runner 不负责人工 OAuth 恢复交互。若运行中仍触发 `x_api_authorize`，应归为 `ERROR`，提示环境未预授权。

### pending 数量检查不进入 runner

如果把 pending 计数前后对比加入 examples，会将 SDK runner 强绑定到 Agent 数据准备和数据库状态，复杂度明显失控，因此本次明确不做。

## 最终结论

本次更新后的 `X Capability E2E` 应保持一个单一、清晰的角色：

它是一个 **SDK 侧自动矩阵 runner**，只负责验证 12 个可稳定断言的能力路径。

而 `auto`、pending 数量、扩展中途断开、fail-fast、popup 和 task start 日志这类 Agent 运行态问题，统一通过 README 中的手动 smoke 命令验证。

这个边界能够同时满足：

- 覆盖核心能力矩阵
- 对齐 Agent 最新执行模式语义
- 避免 examples 项目过度设计
- 避免把 SDK runner 扩张成 Agent 调试工具
