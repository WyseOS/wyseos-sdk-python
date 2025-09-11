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