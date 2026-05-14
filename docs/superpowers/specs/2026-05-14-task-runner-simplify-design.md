# TaskRunner 精简拆解设计

- 日期：2026-05-14
- 状态：待评审
- 范围：在不改变 SDK 公开 API 形状的前提下，收敛 `TaskRunner` 的内部职责，明确授权恢复语义，删除无收益状态机，降低 CLI / 浏览器交互与核心编排的耦合。

## 1. 背景与目标

当前 `TaskRunner` 的主要问题不是“功能不够多”，而是核心职责混杂，导致默认入口行为、交互恢复语义、遗留接口定位和内部状态复杂度之间互相拉扯。

本次设计目标有四个：

1. 保持公开 API 不变。
2. 将 SDK 核心语义收敛为“可恢复失败闭环”，而不是“自动阻塞等待人工恢复”。
3. 仅做最小抽取，避免为了未来可能的演进引入新的大层级和通用抽象。
4. 删除没有真实收益的内部状态与残留结构，降低维护成本。

这里对“SDK 主入口闭环”的定义是：

- 高层默认入口 `run_task()` 能对授权中断给出稳定、一等、可恢复的结果语义；
- 而不是把调用方推去另一个入口，或把授权中断伪装成普通失败；
- 也不是要求 SDK 核心替调用方自动进入阻塞式人工恢复流程。

## 2. 设计约束

本次设计遵守以下约束：

1. 不修改 `TaskRunner`、`run_task()`、`run_interactive_session()`、`TaskResult` 的公开名称与基本调用方式。
2. 不新增新的公开返回类型，不把“授权等待态”暴露为新的公共对象。
3. 不对 `UserService` 的旧 X OAuth 接口做破坏性删除或签名调整。
4. 不引入通用 `InteractionAdapter`、`SessionController`、全局状态机等面向未来的抽象。
5. 不借机重做 plan、browser、marketing report 等现有分支。
6. 不新增单元测试文件；验证方式保持为 `compileall` 与一次性脚本。

## 3. 问题归纳

### 3.1 默认主入口没有实现完整闭环

当前 `run_task()` 一旦收到 `x_api_authorize`，仍直接走非交互失败分支。结果是：

- SDK 的高层默认入口不能自然表达“这是一个需要授权恢复的中断”；
- 调用方必须预先知道自己要切到 `run_interactive_session()`；
- 自动任务与远程任务的失败语义不稳定，容易滑向长时间等待或错误引导。

### 3.2 协议编排与 CLI / 浏览器交互混在一起

`TaskRunner` 当前同时承担：

- WebSocket 生命周期管理
- 协议消息分发
- 任务运行状态管理
- CLI 输出
- 浏览器打开
- 终端输入恢复

这让核心 runner 无法清晰区分：

- 哪些是 SDK 核心语义
- 哪些只是 CLI 宿主体验

### 3.3 marketing chunk buffer 复杂度高但不产出真值

现有 marketing stream 路径在 SDK 侧维护 chunk buffer，但最终结果并不使用这份 buffer，而是在 stream end 后重新调用 HTTP 汇总接口拉取全量数据。

这说明：

- chunk buffer 不是结果真值；
- 它只是额外的运行时复杂度；
- 为它引入的锁、重置逻辑和状态维护没有形成实际收益。

### 3.4 旧 X OAuth 接口仍是公共表面，但已不属于主闭环

`UserService` 中的：

- `get_x_oauth_url()`
- `list_x_accounts()`
- `authorize_x_account()`

仍然存在，但当前正确的 same-round authorize 语义已经迁移到 agent 下发的：

- `auth_url`
- `request_id`
- 当前轮次恢复

因此这些接口不再应被视为 runner 主闭环的一部分，而应明确定义为 legacy / 手工辅助能力。

### 3.5 execution_mode 已是一等参数，但内部仍有双入口语义

对外已经暴露 `execution_mode` 参数，但内部仍可从：

- 显式 `execution_mode=...`
- `extra["execution_mode"]`

两处读取同一语义。即使公开 API 暂时不能改，这种双入口也必须在内部尽快收敛成单一真值。

### 3.6 代码里仍有明显残留结构

当前还能看到两类典型残留：

1. 未使用的定义，例如 `TaskStatus`
2. 可变默认值，例如 `TaskResult` 与 `EventLog` 中的列表 / 字典默认值

这些问题单独看不大，但它们会持续污染核心层的边界感。

## 4. 核心设计选择

### 4.1 SDK 核心语义：可恢复失败闭环

本次设计明确采用：

- `run_task()`：可恢复失败闭环
- `run_interactive_session()`：交互恢复闭环

这意味着：

1. `run_task()` 遇到 `x_api_authorize` 时，不阻塞等待人工 OAuth。
2. `run_task()` 也不应尝试偷偷进入 CLI 风格的 `input()` 恢复。
3. 它应快速返回一个普通 `TaskResult(success=False, error=...)`。
4. 但这个失败必须是一种稳定、明确、可恢复的失败，而不是普通的未知错误。

这样定义的原因是：

- 对 SDK 使用者，最危险的是无人值守任务假死或长时间挂起；
- 对 CLI 使用者，阻塞式人工恢复可以作为宿主体验存在，但不应成为 SDK 核心默认语义；
- SDK 核心只需要清晰表达“当前任务因授权中断，且可以继续恢复”，不需要替所有宿主实现恢复体验。

### 4.2 最小抽取：只新增 AuthorizationCoordinator

为了避免过度设计，本次不引入更大的控制器层，也不单独抽完整 `RunState`。

只新增一个内部模块与两个极小对象：

1. `AuthorizationState`
2. `AuthorizationCoordinator`

其中：

- `AuthorizationState` 只表示当前是否处于授权等待态，以及与恢复相关的极少量字段；
- `AuthorizationCoordinator` 只负责授权请求识别、状态更新、恢复提示生成、失败错误生成。

除此以外：

- `TaskRunner` 继续是公开 facade；
- `TaskRunner` 继续保留主循环、消息分发、连接管理和结果组装；
- 不额外抽象通用交互层。

这是本次设计最关键的“克制点”。

## 5. 新的内部职责边界

### 5.1 TaskRunner 保留职责

`TaskRunner` 继续负责：

1. WebSocket handler 注册
2. connect / disconnect 生命周期
3. `run_task()` 与 `run_interactive_session()` 主循环
4. WebSocket 消息分发
5. `TaskResult` 组装
6. 既有 plan / rich / task_result / error 分支

本次不改变它作为公开入口 facade 的定位。

### 5.2 AuthorizationCoordinator 职责

`AuthorizationCoordinator` 只负责：

1. 判断消息是否为 `x_api_authorize`
2. 校验 payload 是否满足同轮恢复要求
3. 将授权请求转换为内部 `AuthorizationState`
4. 生成自动入口的可恢复失败错误文案
5. 生成交互入口的恢复提示文案
6. 在交互入口下，根据用户回车生成 resume input payload
7. 在恢复完成或失败后清空授权状态

它不负责：

1. WebSocket 发送
2. HTTP stop
3. 最终 TaskResult 组装
4. 其它类型消息处理

### 5.3 CLI / 浏览器交互边界

本次不引入通用 IO 抽象，但要明确一条规则：

- `run_task()` 不承担人工交互职责
- `run_interactive_session()` 保留 CLI 交互职责

因此：

1. `run_task()` 遇到授权恢复时，不做 `input()`，不做等待。
2. `run_interactive_session()` 遇到授权恢复时，仍可输出 URL、提示用户回车、发送 `continue`。
3. 浏览器打开逻辑只在交互语义下保留；自动入口只允许给出恢复信息，不承担宿主体验。

这已经足够实现边界收敛，不需要再为未来宿主泛化出额外交互接口。

## 6. 授权状态机

授权状态机只保留三种内部状态：

1. `idle`
2. `pending_authorization`
3. `terminal_failure`

### 6.1 idle

默认状态，没有待恢复授权。

### 6.2 pending_authorization

收到合法的 `x_api_authorize` payload 后进入此状态，内部仅记录：

1. `request_id`
2. `auth_url`
3. `reason_code`
4. 恢复提示文本

这里不记录额外的运行态信息，不引入“未来可能会用到”的字段。

### 6.3 terminal_failure

当授权事件本身不合法时进入，例如：

1. 缺 `request_id`
2. 缺 `auth_url`

这类情况属于协议错误，不应再尝试恢复。

## 7. 两个高层入口的行为定义

### 7.1 run_task()

`run_task()` 收到 `pending_authorization` 后：

1. 不等待
2. 不 prompt
3. 不尝试本地浏览器恢复
4. 立即走 fail-fast
5. 返回普通 `TaskResult(success=False, error=...)`
6. 保持当前已有的 stop / HTTP stop 兜底行为，确保自动任务快速退出

此时 `error` 由 coordinator 统一生成，建议使用稳定前缀，例如：

```text
authorization_required: X authorization is required to continue this task.
```

并可附带：

- `Authorization URL: ...`
- `Use run_interactive_session() to resume.`

这样调用方可以稳定识别授权中断，而不是解析随意文案。

### 7.2 run_interactive_session()

`run_interactive_session()` 收到 `pending_authorization` 后：

1. 输出 `auth_url`
2. 输出恢复提示
3. 等待用户回车
4. 发送 `continue`
5. 清空授权状态
6. 回到正常任务循环

这里的恢复仍然走当前会话、当前 `request_id`，保持 same-round resume 语义。

### 7.3 协议错误场景

若 coordinator 给出 `terminal_failure`：

1. `run_task()` 直接失败返回
2. `run_interactive_session()` 直接报错并结束本轮

不再尝试任何 fallback。

## 8. execution_mode 内部收敛

公开 API 保持现状，但内部只保留一个真值。

规则如下：

1. 若显式传入 `execution_mode=...`，它是内部真值。
2. 否则读取 `extra["execution_mode"]` 作为兼容输入。
3. 标准化后，内部只保留一个解析结果。
4. 发送给 agent 前，再把这个单一结果写回请求 `extra`。

约束：

- 后续所有内部逻辑不得再次直接读取原始 `extra["execution_mode"]`
- 所有判断都只能使用标准化后的单一值

这能在不破坏公开 API 的前提下，消除双真值问题。

## 9. marketing chunk buffer 的处理

本次设计建议直接删除 marketing chunk buffer。

删除项：

1. `_marketing_chunk_buffers`
2. `_marketing_buffer_lock`
3. 与 chunk buffer 初始化、写入、reset 相关的内部逻辑

保留行为：

1. chunk 到达时，如果 `verbose` 或 event logging 开启，可以继续输出简短日志
2. stream end 后，继续沿用 `get_marketing_data()` 获取最终汇总结果

原因：

- 当前 chunk buffer 不是真值
- 当前 chunk buffer 不参与结果组装
- 当前 chunk buffer 的存在只增加并发与生命周期复杂度

这属于“有复杂度、无收益”的典型结构，应直接移除，而不是继续修补。

## 10. UserService 中旧 X OAuth 接口的定位

以下接口保留公开 API：

1. `get_x_oauth_url()`
2. `list_x_accounts()`
3. `authorize_x_account()`

但本次在设计上明确：

- 它们不属于当前 runner 的 same-round authorize 主闭环
- 不再参与 `TaskRunner` / `AuthorizationCoordinator` 的授权恢复链路
- 它们只保留为 legacy surface 或手工辅助接口

这样做的作用是：

1. 保持兼容
2. 避免再次把旧 OAuth URL 生成逻辑塞回主闭环
3. 明确主链路只认 agent 下发的 `auth_url + request_id`

## 11. 残留清理

本次顺手清理以下低风险残留：

1. 删除未使用的 `TaskStatus`
2. 将 `TaskResult`、`EventLog` 中的可变默认值改为 `default_factory`
3. 删除与旧授权分支相关的死字段、死 helper、重复状态

这些清理不应扩大到无关模块。

## 12. 明确不改的内容

本次设计明确不做以下事情：

1. 不重命名公开入口
2. 不新增新的公开返回模型
3. 不把授权等待态公开暴露
4. 不做 `UserService` 弃用流程
5. 不引入通用交互适配层
6. 不重做 plan / browser / report 等其他分支
7. 不引入新的测试框架或单元测试文件

## 13. 推荐文件改动

### 13.1 新增

新增内部文件：

```text
octoevo/mate/task_authorization.py
```

内容仅包含：

1. `AuthorizationState`
2. `AuthorizationCoordinator`

### 13.2 修改

修改：

1. `octoevo/mate/task_runner.py`
2. `octoevo/mate/websocket.py`
3. `octoevo/mate/__init__.py`

其中：

- `task_runner.py` 是本次主要改动点
- `websocket.py` 只做与当前 runner 语义直接相关的残留清理
- `__init__.py` 只做必要导出调整

### 13.3 不改

不修改：

1. `UserService` 公开签名
2. examples / quickstart 的结构性设计

如需更新示例，应放在后续独立实现步骤，不并入本次拆解设计的核心判断。

## 14. 验证标准

### 14.1 自动入口

1. `run_task()` 遇到 `x_api_authorize` 时必须快速返回
2. `run_task()` 不得触发 `stdin` 读取
3. 返回的错误必须能稳定表达“授权中断，可恢复”
4. 自动入口仍会触发 stop / HTTP stop，避免任务空转

### 14.2 交互入口

1. `run_interactive_session()` 遇到 `x_api_authorize` 时能展示 URL
2. 用户回车后能继续当前轮次任务
3. 仍然使用同一 `request_id` 恢复

### 14.3 execution_mode

1. 同时存在显式参数与 `extra["execution_mode"]` 时，显式参数优先
2. 内部只能保留一个标准化结果

### 14.4 marketing

1. 删除 chunk buffer 后，marketing 最终汇总结果不变
2. verbose/event logging 不丢失必要流式观察能力

### 14.5 legacy surface

1. `UserService` 旧 X OAuth 方法仍然可独立调用
2. runner 主链路不再依赖它们

## 15. 最终结论

本次推荐方案是：

1. 保持 `TaskRunner` 公开 facade 不变
2. 只新增一个极小的 `AuthorizationCoordinator`
3. 将 SDK 核心语义明确为“可恢复失败闭环”
4. 删除 marketing chunk buffer 这套无收益状态机
5. 将旧 `UserService` X OAuth 能力明确降为 legacy surface
6. 顺手清理少量核心残留

这是在当前约束下最克制、最直接、最不面向未来的一版拆解方案。

它解决的是当前真实存在的问题，而不是为未来假设搭骨架。
