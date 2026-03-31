## 🚀 Release 0.3.1 (2026-03-31)

### ✨ Major Features

- **📦 Product Analysis Service**: New `ProductService` for the full product analysis lifecycle — create, poll, and retrieve reports via REST API (no WebSocket needed).
  - `client.product.create()` — submit product name or URL with optional attachments
  - `client.product.get_info()` — poll product generation status
  - `client.product.get_report()` — get full analysis report (keywords, personas, competitors, campaigns)
  - `client.product.get_categories()` — retrieve industry classification data
  - `client.product.create_and_wait()` — high-level method that handles the entire create → poll → report flow with callback support
- **📊 Product Data Models**: Typed Pydantic models for the product API: `CreateProductRequest`, `CreateProductResponse`, `ProductInfo`, `ProductReport`, `Campaign`, `IndustryCondition`, `Category`, `Industry`

### 🔧 Improvements

- **🔇 Cleaner Logging**: WebSocket connection URL (containing credentials) moved from `INFO` to `DEBUG`; disconnect internals also demoted to `DEBUG`
- **📋 Better CLI Output**: Plan status updates now use `[plan] status: xxx` format; task result shows `[task_result] completed/stopped`; JSON completion messages parsed to display human-readable reason instead of truncated raw JSON
- **🛡️ Example Robustness**: Both examples now exit cleanly with a helpful message when `mate.yaml` is missing or has invalid credentials, instead of falling back to empty defaults

### 📝 New Files

- `wyseos/mate/services/product.py` — ProductService implementation
- `examples/product_analysis/example.py` — standalone product analysis example
- `docs/api-product-create.md` — product API documentation (Chinese)

📦 See: [wyseos-sdk 0.3.1 on PyPI](https://pypi.org/project/wyseos-sdk/)

## 🚀 Release 0.3.0 (2026-03-31)

### ✨ Major Features

- **🎯 Marketing Mode**: Full marketing support — product analysis, trending topic selection, tweet/thread generation, and rich streaming with chunk aggregation.
  - New `TaskMode.Marketing` for marketing-specific session execution
  - New `MarketingService` with REST APIs: `get_product_info`, `get_report_detail`, `update_report`, `get_research_tweets`
  - New `SessionService.get_marketing_data()` for retrieving generated content (reply/like/retweet/tweet) per session
  - Rich streaming support for `writer_twitter`, `marketing_tweet_reply`, `marketing_tweet_interact`
- **🔑 JWT Authentication**: Dual auth support — API key and JWT token, across both HTTP and WebSocket.
- **🛑 CLI Safe Mode**: `stop_on_x_confirm` option to prevent browser actions in headless/CLI environments.
- **⏸️ Session Pause**: New `send_pause()` for pausing active sessions.

### 🔧 Improvements

- **📦 TaskRunner Refactor**: Extracted `TaskRunner`, `TaskExecutionOptions`, `TaskResult`, and `TaskMode` out of `websocket.py` into dedicated `task_runner.py` (~500 lines reduction in websocket module).
- **🔇 Cleaner CLI Output**: Debug logs moved from `INFO` to `DEBUG` level; verbose output uses consistent `[plan]`/`[text]`/`[task_result]` prefixes; JSON completion messages parsed to show human-readable reason.
- **📋 Session Protocol Alignment**: `CreateSessionRequest` simplified (removed `team_id`, added `mode`/`platform`/`extra`); `SessionInfo` fields made lenient with sensible defaults.
- **🏭 Factory Function**: `create_task_runner()` exposed at package level for clean initialization.

### 🐛 Bug Fixes

- Fixed `auto_accept_plan` not working in `run_interactive_session`
- Fixed session not stopping after receiving final answer
- Fixed screenshot printing to omit large base64 data

### 💥 Breaking Changes

- `CreateSessionRequest` no longer requires `team_id`
- Session status constants renamed: `SESSION_STATUS_RUNNING` → `SESSION_STATUS_ACTIVE`
- Plan status `SKIPPED` renamed to `SKIP`

📦 See: [wyseos-sdk 0.3.0 on PyPI](https://pypi.org/project/wyseos-sdk/)

## 🚀 Release 0.2.1 (2025-09-11)

### ✨ Major Features

- **🎯 New: TaskRunner Interface**: Simplified task execution interface that reduces complex WebSocket operations from 400+ lines to 10-20 lines of clean code.
  - `run_task()` - Automated execution with comprehensive results
  - `run_interactive_session()` - Interactive mode with user input support
- **⚙️ New: TaskExecutionOptions**: Advanced configuration system with intelligent defaults including performance-optimized screenshot capture (`capture_screenshots=False` by default).
- **📊 New: Enhanced Result Tracking**: Complete `TaskResult` model with execution duration, message counts, plan history, and structured error reporting.

### 🔧 Improvements

- **📦 Refactored Message Handling**: Modular message processing with dedicated handlers for text, plan, rich media, and input messages.
- **📚 Enhanced Documentation**: Complete rewrite of quickstart guide and README with modern examples and clear API documentation.
- **⚡ Performance Optimizations**: Default settings optimized for speed with conditional data collection and reduced memory usage.
- **🛡️ Improved Error Handling**: Enhanced exception management with detailed error context and graceful resource cleanup.

### 🐛 Bug Fixes

- **🧵 Enhanced Thread Safety**: Improved thread-safe completion event handling for concurrent operations.
- **🔌 Connection Management**: Better WebSocket connection lifecycle management with proper cleanup.

📦 See: [wyseos-sdk 0.2.1 on PyPI](https://pypi.org/project/wyseos-sdk/)

## 📦 Release 0.2.0 (2025-08-25)

### 💥 Breaking Changes

- **🏷️ Project Renamed**: The SDK has been renamed from `wyse-mate-sdk` to `wyseos-sdk`. All module imports must be updated from `wyse_mate` to `wyseos.mate`.
  - **Before**: `from wyse_mate import Client`
  - **After**: `from wyseos.mate import Client`

### 🔧 Improvements

- **🏗️ Project Restructuring**: Aligned project with the `WyseOS` and established a new, extensible namespace `wyseos` for future tools.
- **⚙️ Simplified Configuration**: Removed `user_agent`, `debug`, and `http_client` from the configuration options for a cleaner setup.
- **📚 Added Examples**: Introduced a new `examples` directory with a `getting_started` guide to improve user onboarding.

### 🐛 Bug Fixes

- **🚫 Fixed `ImportError`**: Resolved an `ImportError` for `DEFAULT_USER_AGENT` that occurred after simplifying the configuration.
- **✅ Fixed `ValidationError`**: Addressed a `ValidationError` by making the `intent_id` field in the `SessionInfo` model optional to handle missing fields in the API response.

📦 See: [wyseos-sdk 0.2.0 on PyPI](https://pypi.org/project/wyseos-sdk/)

## 📦 Release 0.1.2 (2025-08-08)

### 🔧 Improvements

- 🆕 New: Plan messages with overall status tracking
- 🆕 New: Expanded WebSocket interactions and stability
- 📈 Improvement: Clearer usage in examples

📦 See: [wyse-mate-sdk 0.1.2](https://pypi.org/project/wyse-mate-sdk/)

### 📝 Commits

- [6d52b80 — release version 0.1.2](https://github.com/WyseOS/mate-sdk-python/commit/6d52b80)
- [dda05b0 — add plan overall status](https://github.com/WyseOS/mate-sdk-python/commit/dda05b0)
- [bcec77d — add message type Plan](https://github.com/WyseOS/mate-sdk-python/commit/bcec77d)
- [09c20ad — update example](https://github.com/WyseOS/mate-sdk-python/commit/09c20ad)
- [77fe5b3 — update example](https://github.com/WyseOS/mate-sdk-python/commit/77fe5b3)
- [fb6fef6 — support more websocket interactions](https://github.com/WyseOS/mate-sdk-python/commit/fb6fef6)

### 👥 Come Hang Out

- 🐛 Found a bug? Open an issue on [Github](https://github.com/WyseOS/mate-sdk-python/issues)
