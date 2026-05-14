## 🚀 Release 0.1.2 (2026-05-14)

This release improves the SDK's core session runner behavior for non-interactive environments and makes WebSocket shutdown more reliable.

### ✨ Improvements

- **Safer `run_task()` input handling**: non-interactive runs now fail clearly when the agent requires user input, instead of hanging or leaving the task in an ambiguous state.
- **Built-in `x_api_authorize` handling**: the core runner now recognizes X API authorization input messages, surfaces the authorization URL, and skips by default in non-interactive mode with a clear error.
- **Cleaner history filtering**: `TaskRunner` now ignores replayed history messages during automated runs, reducing false state transitions from old session events.

### 🛠️ Engineering

- **More robust WebSocket disconnects**: shutdown now tolerates benign timeout / closed-loop races and avoids noisy close failures during normal teardown.
- **Stable local WebSocket host resolution**: `localhost` is normalized for WebSocket connection setup to reduce local connectivity inconsistencies.
- **Clearer runner state management**: pending input state and skipped-authorization state are now tracked explicitly inside `TaskRunner`.

## 🚀 Release 0.1.0 (2026-04-28)

Initial release of the **OctoEvo** Python SDK — a unified client for OctoEvo's agent, marketing, and product-analysis platform.

### ✨ Features

- **🤖 Multi-Agent Task Execution**: `TaskRunner` interface wraps the full WebSocket session lifecycle.
  - `run_task()` — automated, fire-and-forget execution returning a structured `TaskResult`
  - `run_interactive_session()` — interactive mode with user-input support and `auto_accept_plan`
  - `TaskExecutionOptions` for screenshot capture, plan handling, and CLI safe mode (`stop_on_x_confirm`)
- **🎯 Marketing Mode**: End-to-end marketing workflows with `TaskMode.Marketing`.
  - `MarketingService`: product info, report detail/update, research tweets
  - `SessionService.get_marketing_data()` for generated reply / like / retweet / tweet content
  - Rich streaming with chunk aggregation for `writer_twitter`, `marketing_tweet_reply`, `marketing_tweet_interact`
- **📦 Product Analysis Service**: REST-only product lifecycle — no WebSocket required.
  - `client.product.create()` / `get_info()` / `get_report()` / `get_categories()`
  - `client.product.create_and_wait()` — high-level create → poll → report flow with callback
  - Typed models: `CreateProductRequest`, `ProductInfo`, `ProductReport`, `Campaign`, `Industry`, `Category`
- **🔑 Dual Authentication**: API key and JWT token, supported across HTTP and WebSocket transports.
- **⏸️ Session Control**: `send_pause()` for active sessions; clean stop on final answer; plan status tracking with overall state.
- **🧩 Service Coverage**: `agent`, `browser`, `file_upload`, `marketing`, `product`, `session`, `team`, `user`.

### 🛠️ Engineering

- Modular message handlers for text, plan, rich media, and input messages
- `create_task_runner()` factory exposed at package level
- Lenient Pydantic models with sensible defaults for forward compatibility
- Performance defaults: `capture_screenshots=False`, conditional data collection
- Consistent CLI prefixes: `[plan]` / `[text]` / `[task_result]`; credentials kept out of `INFO` logs

### 📦 Install

```bash
pip install octoevo
```

📦 See: [octoevo on PyPI](https://pypi.org/project/octoevo/)
