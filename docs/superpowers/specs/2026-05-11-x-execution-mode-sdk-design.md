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
5. 将实现控制在 SDK 运行时 helper 和 `TaskRunner` 内，保持改动小而直接。

## 非目标

1. 不修改 Go 后端 API。
2. 不新增公开 runner option。
3. 不新增轮询 OAuth 回调完成状态的机制。
4. 不在 OAuth 完成后自动重试被中断的 agent 任务。
5. 不新增单元测试文件。

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

新增一个很小的 SDK 内部浏览器可用性 helper。

默认状态：

```python
could_use_browser = False
```

SDK 可以暴露一个最小 setter，供明确知道本地浏览器可用的调用方使用：

```python
set_browser_available(True)
```

这不是 runner option，也不应该出现在主 CLI 使用路径中。它只是给本地集成场景保留的显式 opt-in 出口。

所有面向用户的 URL 交互都应该经过同一个 helper：

1. 如果 `could_use_browser` 为 false，只打印 URL 和一句简短说明。
2. 如果 `could_use_browser` 为 true，尝试打开 URL。
3. 如果打开失败，记录日志并打印 URL。

这个 helper 应同时替换当前 `x_confirm` 里直接调用 `webbrowser.open()` 的行为，并用于新增的 `x_api_authorize` 路径。

## x_api_authorize 输入处理

`TaskRunner._handle_input_message()` 应在普通 plan 或 text input 处理之前识别 `x_api_authorize`。

识别逻辑需要宽松，因为 payload 可能通过 metadata 或消息内容到达：

1. `message.message.type == "x_api_authorize"`
2. `message.message.metadata.data_type == "x_api_authorize"`
3. `message.message.data.type == "x_api_authorize"`
4. 文本 content 可解析为 JSON，且其中 `type == "x_api_authorize"`

预期 payload：

```json
{
  "type": "x_api_authorize",
  "session_id": "...",
  "execution_mode": "api_only",
  "external_user_id": "...",
  "external_username": "...",
  "reason_code": "...",
  "reason_message": "..."
}
```

SDK 在打印授权 URL 后不应该发送伪造的 approval response。OAuth 完成是带外流程。用户或调用方 agent 完成授权后，应通过现有会话输入机制继续下一轮任务。

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
5. 如果没有匹配账号，传 `None`。

这样可以将 agent 的原因码映射到后端行为：

1. `TOKEN_EXPIRED`：通常能匹配已有 connector，重签同一个 credential。
2. `INSUFFICIENT_SCOPE` / `ACCOUNT_SCOPE_MISSING`：通常能匹配已有 connector，按后端当前 Twitter scopes 重新授权。
3. `AUTH_REQUIRED` / `CREDENTIAL_NOT_FOUND`：如果没有匹配 connector，则创建新绑定。
4. `ACCOUNT_IDENTIFIER_REQUIRED`：没有可靠目标账号，创建新绑定。

如果列出 connectors 失败，SDK 仍应调用 `authorize_x_account(None)`，并打印或记录“无法定位已有 credential”的信息。

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

如果 `could_use_browser` 为 true 但打开 URL 失败：

1. 用英语记录 warning 日志。
2. 打印 URL。

## 需要修改的文件

1. `octoevo/mate/task_runner.py`
   - 增加宽松的 `x_api_authorize` 识别。
   - 增加 handler：列出 connectors、选择 `target_connector_id`、调用 `authorize_x_account()`，并通过统一 URL helper 输出授权 URL。
   - 让 `x_confirm` 也走同一个 URL helper。

2. `octoevo/mate/browser_runtime.py` 或类似的小模块
   - 保存 `could_use_browser = False`。
   - 提供 `set_browser_available()` 和 `show_or_open_url()`。

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
2. `x_api_authorize` 会打印 connector OAuth URL。
3. 按 `external_user_id` 匹配成功时会传入 `target_connector_id`。
4. 没有匹配账号时会传入 `target_connector_id=None`。
5. `extra.execution_mode` 在 WebSocket start payload 中保持原样透传。
