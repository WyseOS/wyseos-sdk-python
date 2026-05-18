# X Capability E2E

这个目录用于运行真实的 X capability 端到端营销会话，验证 SDK 在不同环境和 capability 组合下的实际行为。

它覆盖的是 **SDK 侧固定 18 个场景矩阵**，不是通用测试框架：

- environment: `local` / `remote`
- capability: `extension` / `api` / `auto`
- task type: `reply` / `publish` / `interact`

当前 **不覆盖** 以下内容：

- messaging 流程
- 任务内交互式 OAuth 恢复

这里的自动 runner 只负责执行和判定结果，不会替你完成授权交互。

## 场景范围

自动 runner 覆盖的 18 个场景如下：

| 场景 ID | environment | capability | task type | execution_mode | 预期结果 |
|---|---|---|---|---|---|
| `local-extension-reply` | `local` | `extension` | `reply` | `extension_only` | `PASS` |
| `local-extension-publish` | `local` | `extension` | `publish` | `extension_only` | `PASS` |
| `local-extension-interact` | `local` | `extension` | `interact` | `extension_only` | `PASS` |
| `local-api-reply` | `local` | `api` | `reply` | `api_only` | `FAIL`，原因为 `REPLY_API_UNSUPPORTED` |
| `local-api-publish` | `local` | `api` | `publish` | `api_only` | `PASS` |
| `local-api-interact` | `local` | `api` | `interact` | `api_only` | `PASS` |
| `local-auto-reply` | `local` | `auto` | `reply` | `auto` | `PASS` |
| `local-auto-publish` | `local` | `auto` | `publish` | `auto` | `PASS` |
| `local-auto-interact` | `local` | `auto` | `interact` | `auto` | `PASS` |
| `remote-extension-reply` | `remote` | `extension` | `reply` | `extension_only` | `FAIL`，原因为 `EXTENSION_REQUIRED` |
| `remote-extension-publish` | `remote` | `extension` | `publish` | `extension_only` | `FAIL`，原因为 `EXTENSION_REQUIRED` |
| `remote-extension-interact` | `remote` | `extension` | `interact` | `extension_only` | `FAIL`，原因为 `EXTENSION_REQUIRED` |
| `remote-api-reply` | `remote` | `api` | `reply` | `api_only` | `FAIL`，原因为 `REPLY_API_UNSUPPORTED` |
| `remote-api-publish` | `remote` | `api` | `publish` | `api_only` | `PASS` |
| `remote-api-interact` | `remote` | `api` | `interact` | `api_only` | `PASS` |
| `remote-auto-reply` | `remote` | `auto` | `reply` | `auto` | `FAIL`，原因为 `EXTENSION_REQUIRED` |
| `remote-auto-publish` | `remote` | `auto` | `publish` | `auto` | `PASS` |
| `remote-auto-interact` | `remote` | `auto` | `interact` | `auto` | `PASS` |

说明：

- `local` 表示本机可用浏览器，runner 会把 `browser_available=True` 传给 `TaskRunner`
- `remote` 表示无本机浏览器，runner 会把 `browser_available=False` 传给 `TaskRunner`
- `extension` capability 对应 `execution_mode=extension_only`
- `api` capability 对应 `execution_mode=api_only`
- `auto` capability 对应 `execution_mode=auto`

## 运行前准备

先复制配置文件：

```bash
cp mate.yaml.example mate.yaml
```

然后在 `mate.yaml` 中配置可用的 SDK 凭据，例如 `api_key` 或 `jwt_token`。

## 环境变量

运行前请按需设置以下环境变量：

```bash
export MATE_E2E_REPLY_TWEET_URL="https://x.com/user/status/123"
```

各变量含义如下：

| 变量名 | 是否必需 | 说明 |
|---|---|---|
| `MATE_E2E_REPLY_TWEET_URL` | `reply` 必需 | reply 场景的目标推文链接；也可用 `--reply-tweet-url` 传入。publish 和 interact 场景不使用。 |

任务超时默认使用代码内的 `900` 秒；用户输入等待超时默认使用代码内的 `120` 秒。
publish 场景的推文标记前缀默认使用代码内常量 `fictions:`。

E2E 会使用内置默认产品，通过结构化 `extra.marketing_product.product_id` 注入产品上下文。提示词中只包含产品名称，不要求调用方通过环境变量传产品信息。

## 授权前提

API 场景要求目标 X 账号已经完成预授权。

这个 runner **不会执行交互式 OAuth 恢复**。如果执行过程中触发 `x_api_authorize`，当前行为是：

- 打印授权相关消息
- 在无可用终端输入的场景下快速结束
- 结果被归类为 `FAIL`
- `matched_reason` 为 `authorization_required`

因此，这个目录更适合验证：

- 已经准备好授权和账号标识时的正常闭环
- 缺少能力、能力不支持、环境不满足时的预期失败

而不是验证任务内人工授权恢复流程。

## 执行模型

每个场景都会分两步执行：

1. seed 阶段：先创建当前 session 所需的草稿或待执行记录
2. execute 阶段：再在同一个 session 中执行真正的 reply / publish / interact

补充说明：

- `execute` 阶段会显式通过 `run_task(..., execution_mode=...)` 传入 `api_only`、`extension_only` 或 `auto`
- `seed` 阶段不强制 capability 模式，只负责准备会话数据
- `reply` 场景在 `local` 环境下，如果首次 seed 没有产出记录，runner 会尝试一次浏览器 fallback seed

## 运行方式

示例：

```bash
python main.py --all
python main.py --capability extension
python main.py --capability auto
python main.py --environment remote
python main.py --task-type reply
python main.py --scenario local-api-publish
```

CLI 规则：

- 必须指定 `--all` 或至少一个过滤参数，否则程序直接退出
- `--all` 表示显式确认运行全部 18 个场景
- `--all` 不能与任何过滤参数混用
- 多个过滤参数同时出现时，取交集

参数说明：

| 参数 | 可选值 | 说明 |
|---|---|---|
| `--all` | — | 运行全部 18 个场景。它是“显式全量执行开关”，不是过滤条件。 |
| `--scenario <id>` | 见上表 | 只运行一个精确场景 ID。 |
| `--environment <env>` | `local` / `remote` | 按运行环境过滤。 |
| `--capability <cap>` | `extension` / `api` / `auto` | 按 capability 过滤。 |
| `--task-type <type>` | `reply` / `publish` / `interact` | 按任务类型过滤。 |
| `--reply-tweet-url <url>` | X/Twitter 推文 URL | reply 场景目标推文链接；优先级高于 `MATE_E2E_REPLY_TWEET_URL`。 |

## 结果判定

CLI 最终状态只会落在这四类：

- `PASS`
- `FAIL`
- `ERROR`
- `TIMEOUT`

判定原则：

- 预期成功且实际完成目标动作，记为 `PASS`
- 预期失败且观察到对应失败原因，记为 `PASS`
- 明确的授权缺失、能力拒绝、执行闭环失败，通常记为 `FAIL`
- 运行环境或数据准备异常，通常记为 `ERROR`
- 超时记为 `TIMEOUT`

几个关键结果语义：

- `REPLY_API_UNSUPPORTED`：reply 在 `api_only` 下不支持，属于预期失败
- `EXTENSION_REQUIRED`：`remote + extension_only` 无法执行，属于预期失败
- `authorization_required`：表示当前场景需要授权，但 runner 不负责交互式恢复，结果记为 `FAIL`
- `ACCOUNT_IDENTIFIER_REQUIRED`：缺少 X 账号标识，结果记为 `ERROR`
- `missing_pending_records`：seed 阶段没有成功准备出待执行营销记录，结果记为 `ERROR`

## 输出文件

运行结束后，结果会写入：

- `results/latest.json`：结构化报告，包含 run id、时间范围、汇总统计和每个场景的明细结果
- `results/latest.log`：详细执行日志，包含 `final_answer`、`error`、`execution_logs` 和断言结果

`latest.json` 的 summary 字段包含：

- `passed`
- `failed`
- `errors`
- `timeouts`
- `total`

## 适用边界

这个目录适合做的事情：

- 回归验证 18 个固定 SDK capability 场景
- 检查 capability 选择与环境约束是否符合预期
- 观察真实 session 执行日志和最终结构化结果

这个目录不适合做的事情：

- 验证 messaging 类流程
- 验证任务内 same-round 交互式 OAuth 恢复
- 替代 agent 仓库中的更底层 capability / browser 手工烟测

## 手工烟测

以下检查不在这个 SDK 自动 runner 的覆盖范围内，需要到 agent 仓库执行：

1. `api_only + reply=10`

```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --task "只处理当前会话中的待回复推文"
```

预期：没有入口拦截；reply 返回 `REPLY_API_UNSUPPORTED`；待回复记录仍保留。

2. `api_only + interact=5, draft=10 + missing identity`

```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only
```

预期：返回 `ACCOUNT_IDENTIFIER_REQUIRED`，并带有明确用户提示。

3. `api_only + interact=5, draft=10 + ready identity + authorized credential`

```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --x-account <x_username_or_id>
```

预期：正常走 X API 执行链路。

4. `auto + extension disconnected + reply=10`

```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode auto
```

预期：返回 `EXTENSION_REQUIRED`。

5. `auto + extension connected + draft=10`，中途关闭一次 extension

```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode auto --x-account <x_username_or_id> --task "只发布当前会话中的待发布推文草稿"
```

预期：plan A 正常退出，plan B 接管执行。

6. `extension_only + extension connected + reply=10 + partial failures`

```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode extension_only
```

预期：用户侧失败不会被误判成 `EXTENSION_REQUIRED`。

7. `extension_only + extension disconnected`

```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode extension_only
```

预期：命令快速失败。

8. `api_only` popup suppression

```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --x-account <x_username_or_id>
```

预期：没有 popup 创建日志，也没有 `TASK_STARTED_DEFAULT`。
