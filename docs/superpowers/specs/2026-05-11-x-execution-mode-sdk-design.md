# X Execution Mode SDK 设计

- 日期：2026-05-11
- 状态：待评审
- 范围：让 Python SDK 对齐 agent 端 `XWyseBrowser` 的执行模式和 X API 授权流程。本设计不修改 Go 后端 API。

## 背景

agent 端的 `XWyseBrowser` 已经读取 `extra.execution_mode`，并支持三个取值：

1. `auto`
2. `api_only`
3. `extension_only`

SDK 当前已经会在会话启动时透传 `extra`，但还缺少 API-only X 执行的明确示例，也没有处理 agent 新增的 `x_api_authorize` 交互事件。这个事件会在 X API 凭证缺失、过期或缺少 scope 时由 agent 发出。

SDK 可能运行在本地终端、远程服务器，或被 Codex、OpenClaw 等其它 agent 作为 skill 调用。SDK 不能安全地推断当前环境是否有可用的本地浏览器。

## Go 后端 OAuth 结论

Go 后端有两条不同的 X OAuth 路径。

通用登录路径是：

```text
GET /auth/url?type=login&platform=twitter
```

这条路径用于登录 Mate 用户，并可能签发 JWT 或 API key。它不是 agent X API 执行所需的路径。

connector 绑定路径是：

```text
POST /connectors/v1/x/accounts/authorize
```

这是 SDK 处理 `x_api_authorize` 时应该使用的路径。

connector 授权接口会：

1. 要求当前请求已通过 Mate 用户鉴权。
2. 接收 `redirect_url` 和可选的 `target_credential_id`。
3. 创建 `type=bind`、`platform=twitter`、`scene=connector_x_bind` 的 OAuth state。
4. 将 state 写入 Redis，有效期五分钟。
5. 返回 `auth_url`。

回调处理通过下面的注册完成：

```go
oauth.RegisterSceneCallback(connectors.SceneConnectorXBind, connectors.HandleXConnectorCallback)
```

connector 回调会：

1. 使用 Twitter OAuth code 换取 token。
2. 调用 `/2/users/me` 获取 X 账号信息。
3. 写入或刷新 `mate_connector_credentials`。
4. 重定向到原始 `redirect_url`，并携带 `success=true` 或错误码。

如果请求中带有 `target_credential_id`，后端会在生成授权 URL 前校验该 credential 归属；回调时还会要求本次授权的 Twitter 账号与原 credential 的 `external_user_id` 一致。因此它适合 token 过期重签和缺少 scope 时的重新授权。

## 设计目标

1. 保留 SDK 简单的 `extra` 透传模型。
2. 通过示例让 API-only X 会话变得可发现，不增加复杂的公开抽象。
3. 使用现有 connector OAuth 流程处理 `x_api_authorize`。
4. 默认采用适合远程环境的 URL 输出行为。除非进程被明确标记为可使用浏览器，否则不主动打开浏览器。
5. 确保每个 `TaskRunner` 会话的浏览器可用性状态彼此隔离，不使用模块级全局变量。
6. 将实现控制在协议解析、`TaskRunner` 和少量示例更新内，保持改动小而直接。

## 非目标

1. 不修改 Go 后端 API。
2. 不新增公开 runner option。
3. 不新增轮询 OAuth 回调完成状态的机制。
4. 不在 OAuth 完成后自动重试被中断的 agent 任务。
5. 不新增单元测试文件。

## 已核实的事件流问题

当前 agent 端 `XWyseBrowser._emit_x_api_authorize_interaction()` 会先构造一个 `TextMessage`：

```python
TextMessage(
    content=json.dumps(payload, ensure_ascii=False),
    source=self.name,
    metadata={"data_type": "x_api_authorize"},
)
```

随后调用：

```python
interactive_guard.interact(..., data_type="x_api_authorize", send_description=True)
```

`approval_guard.interact()` 在 `send_description=True` 时会先 yield 上面的 `TextMessage`，再 yield `UserInputRequestedEvent(request_id=...)`。服务端 `mate_helper` 会把前者转成普通 `TEXT` WebSocket 事件，把后者转成 `INPUT` WebSocket 事件。当前 `INPUT` 事件只包含：

```json
{
  "type": "text",
  "data": {
    "request_id": "..."
  }
}
```

也就是说，`external_user_id`、`external_username`、`reason_code` 等 JSON payload 并不在 `INPUT` 事件里。SDK 如果只在 `_handle_input_message()` 中解析文本 JSON，会错过前一条 `TEXT` 事件，无法可靠处理 `x_api_authorize`。

本设计选择 **agent 端协议适配** 作为目标方案：`x_api_authorize` 的全量 payload 必须随 `UserInputRequestedEvent` 进入同一个 `INPUT` 事件，使 SDK 收到的 `INPUT` 事件自包含。SDK 不把“从上一条 TEXT 事件暂存 JSON”作为长期方案，因为这依赖事件顺序和隐式关联，容易在并发、重试、日志过滤或中间代理中失效。

目标 `INPUT` 事件形态应为：

```json
{
  "type": "input",
  "message": {
    "type": "x_api_authorize",
    "data": {
      "request_id": "...",
      "type": "x_api_authorize",
      "session_id": "...",
      "execution_mode": "api_only",
      "external_user_id": "...",
      "external_username": "...",
      "reason_code": "...",
      "reason_message": "..."
    },
    "metadata": {
      "data_type": "x_api_authorize"
    }
  }
}
```

为兼容已经部署的 agent，SDK 实现可以在 `_handle_text_message()` 中增加一个很小的临时暂存兼容层：当收到 `metadata.data_type == "x_api_authorize"` 且 content 是合法 JSON 时，保存到当前 `TaskRunner` 实例的 `_pending_x_api_authorize_payload`。紧随其后的 `INPUT` 事件如果只有 `request_id` 且没有 payload，可以消费这个实例字段。该兼容层只能作为过渡路径，不能替代目标协议。

## Execution Mode

SDK 应继续保持 `CreateSessionRequest.extra` 为 `Dict[str, Any]`，不新增嵌套的 execution-mode model。

示例中直接展示协议字段：

```python
extra = {
    "execution_mode": "api_only",
    "marketing_product": {"product_id": product_id},
}
```

示例中说明允许值：

1. `auto`：由 agent 在浏览器插件和 X API 之间决策。
2. `api_only`：agent 在支持的任务上使用 X API；reply 仍不支持。
3. `extension_only`：agent 要求使用浏览器插件。

agent 仍然是 execution mode 校验和降级的权威来源。SDK 不重复实现 agent 的执行模式决策矩阵。

## 浏览器可用性

浏览器可用性必须绑定在 `TaskRunner` 实例生命周期内，不能使用模块级全局变量。

每个 `TaskRunner` 默认：

```python
self._browser_available = False
```

`TaskRunner` 可以暴露一个很小的实例方法，供明确知道本地浏览器可用的调用方使用：

```python
runner.set_browser_available(True)
```

这不是 runner option，也不应该出现在主 CLI 使用路径中。它只是给本地集成场景保留的显式 opt-in 出口。状态保存在 runner 实例上，不会污染同一进程中的其它会话、其它用户或其它 agent 调用。

所有面向用户的 URL 交互都应该经过同一个 helper：

1. 如果 `self._browser_available` 为 false，只打印 URL 和一句简短说明。
2. 如果 `self._browser_available` 为 true，尝试打开 URL。
3. 如果打开失败，记录日志并打印 URL。

这个 helper 应同时替换当前 `x_confirm` 里直接调用 `webbrowser.open()` 的行为，并用于新增的 `x_api_authorize` 路径。

## x_api_authorize 输入处理

`TaskRunner._handle_input_message()` 应在普通 plan 或 text input 处理之前识别自包含的 `x_api_authorize`。

目标识别逻辑：

1. `message.message.type == "x_api_authorize"`
2. `message.message.metadata.data_type == "x_api_authorize"`
3. `message.message.data.type == "x_api_authorize"`

预期 payload 位于 `message.message.data`：

```json
{
  "request_id": "...",
  "type": "x_api_authorize",
  "session_id": "...",
  "execution_mode": "api_only",
  "external_user_id": "...",
  "external_username": "...",
  "reason_code": "...",
  "reason_message": "..."
}
```

如果 SDK 收到旧协议形态，也就是前一条 `TEXT` 事件里有 JSON、随后的 `INPUT` 事件只有 `request_id`，SDK 可以消费当前 runner 实例上的 `_pending_x_api_authorize_payload` 作为兼容路径。该字段必须在消费后立即清空，且不能跨 runner 共享。

SDK 在打印授权 URL 后不应该发送伪造的 approval response。OAuth 完成是带外流程。用户或调用方 agent 完成授权后，应通过现有会话输入机制继续下一轮任务。

CLI 输出授权 URL 后必须明确提示恢复方式：

```text
请在浏览器中完成授权后，回到此终端按回车键（或输入任意内容）以继续当前任务。
```

这句提示是硬编码的交互文案，用来避免用户在空白 stdin 等待状态下误以为程序卡死。

## Connector 选择

处理 `x_api_authorize` 时，SDK 应调用：

```python
client.user.authorize_x_account(target_connector_id=...)
```

调用前，SDK 应尝试定位已有 connector：

1. 调用 `client.user.list_x_accounts()`。
2. 优先按 `external_user_id` 精确匹配。
3. 其次按 `external_username` 精确匹配。
4. 如果匹配到一个账号，将其 `connector_id` 作为 `target_connector_id`。
5. 如果没有匹配账号，允许传 `None`，但必须先输出强防呆提示。

这样可以将 agent 的原因码映射到后端行为：

1. `TOKEN_EXPIRED`：通常能匹配已有 connector，重签同一个 credential。
2. `INSUFFICIENT_SCOPE` / `ACCOUNT_SCOPE_MISSING`：通常能匹配已有 connector，按后端当前 Twitter scopes 重新授权。
3. `AUTH_REQUIRED` / `CREDENTIAL_NOT_FOUND`：如果没有匹配 connector，则创建新绑定。
4. `ACCOUNT_IDENTIFIER_REQUIRED`：没有可靠目标账号，创建新绑定。

如果 agent payload 携带了 `external_username` 或 `external_user_id`，但 SDK 没有匹配到已有 connector，继续传 `target_connector_id=None` 前必须打印醒目的 warning：

```text
WARNING: Agent 要求执行任务的 X 账号为 @{external_username}（external_user_id={external_user_id}）。
请确保接下来打开的网页中登录并授权的是这个账号，否则当前任务将无法继续。
```

如果没有 `external_username`，只展示 `external_user_id`。如果两个字段都没有，则提示“Agent 未提供目标 X 账号标识，请确认授权账号正确”。

如果列出 connectors 失败，SDK 仍应调用 `authorize_x_account(None)`，但必须打印 warning，说明无法校验目标账号，用户需要自行确认授权账号正确。

## Redirect URL

现有 SDK 的 `UserService.authorize_x_account()` 已经发送：

```text
{extension_webapp_host}/settings/integrations/x/callback?scene=connector_x_bind
```

这与 Go connector callback 兼容。除非后续产品需要 CLI 专用成功页，否则这里不需要 SDK 修改。

## 错误处理

如果 `authorize_x_account()` 失败：

1. 为 CLI 用户打印简短清晰的错误。
2. 在 event logging 开启时增加一条 execution log。
3. 保持任务 pending，不发送成功响应。

如果 `self._browser_available` 为 true 但打开 URL 失败：

1. 用英语记录 warning 日志。
2. 打印 URL。

## 需要修改的文件

1. `octoevo/mate/task_runner.py`
   - 增加自包含 `x_api_authorize` INPUT 事件识别。
   - 增加旧协议兼容暂存：在 TEXT 事件中捕获 `metadata.data_type == "x_api_authorize"` 的 JSON payload，供紧随其后的 INPUT 消费。
   - 增加 handler：列出 connectors、选择 `target_connector_id`、调用 `authorize_x_account()`，并通过统一 URL helper 输出授权 URL。
   - 在未命中目标 connector 时打印强 warning。
   - 在输出授权 URL 后打印“完成授权后回车继续”的恢复提示。
   - 让 `x_confirm` 也走同一个 URL helper。
   - 新增 runner 实例字段 `self._browser_available = False` 和实例 setter，禁止使用模块级全局状态。

2. agent 端 `approval_guard.py` / `mate_helper.py` / `x_web_browser.py` 中最小必要位置
   - 让 `x_api_authorize` 的 payload 进入 `UserInputRequestedEvent` 或其 metadata/data。
   - 确保 WebSocket `INPUT` 事件自包含，不依赖前一条 TEXT 事件。

3. `examples/getting_started/example.py` 和 quickstart 文档
   - 展示 `extra["execution_mode"] = "api_only"` 的 API-only marketing 示例。
   - 保持“输出 URL 后由用户自行完成授权”的文本优先体验。

## 验证

运行：

```bash
python -m compileall octoevo/mate
```

手工检查：

1. `x_confirm` 默认不再尝试打开浏览器。
2. 新协议下，单条 `INPUT` 事件即可携带并触发 `x_api_authorize`。
3. 旧协议下，先到达的 TEXT JSON 能被当前 runner 暂存，并被紧随其后的 INPUT 消费。
4. `x_api_authorize` 会打印 connector OAuth URL。
5. 输出授权 URL 后会提示用户完成授权后回车继续。
6. 按 `external_user_id` 匹配成功时会传入 `target_connector_id`。
7. 没有匹配账号时会传入 `target_connector_id=None`，且先打印强 warning。
8. 多个 `TaskRunner` 实例之间的浏览器可用性状态互不影响。
9. `extra.execution_mode` 在 WebSocket start payload 中保持原样透传。
