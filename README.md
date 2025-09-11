# 🤖 WyseOS SDK for Python

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![PyPI Package](https://img.shields.io/pypi/v/wyseos-sdk)](https://pypi.org/project/wyseos-sdk/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/wyseos-sdk)](https://pypi.org/project/wyseos-sdk/)
[![Documentation](https://img.shields.io/badge/docs-comprehensive-green)](./examples/quickstart.md)

**The official Python SDK for WyseOS** - Build intelligent AI-powered applications with seamless API integration, real-time WebSocket support, and simplified task execution.

> 🚀 **New in v0.2.1**: Simplified task execution interface with `TaskRunner` - execute complex AI tasks with just a few lines of code!

## ✨ What is WyseOS?

WyseOS is an advanced AI platform that enables developers to build sophisticated AI agents and workflows. The Python SDK provides:

- 🎯 **Intelligent Task Execution** - Run complex AI tasks with automatic plan acceptance
- 🔄 **Real-time Communication** - WebSocket integration for live AI interactions  
- 📂 **File Processing** - Upload and analyze documents, images, and data files
- 🌐 **Browser Automation** - AI-powered web browsing and data extraction
- 👥 **Team Management** - Organize AI agents and workflows by teams
- 🛡️ **Enterprise Ready** - Type-safe, robust error handling, and comprehensive logging

## 🚀 Quick Start

### Installation

```bash
pip install wyseos-sdk
```

### 30-Second Example

```python
from wyseos.mate import Client
from wyseos.mate.config import load_config
from wyseos.mate.models import CreateSessionRequest
from wyseos.mate.websocket import WebSocketClient, TaskExecutionOptions

# Initialize client
client = Client(load_config("mate.yaml"))

# Create session
session = client.session.create(
    CreateSessionRequest(team_id="wyse_mate", task="Analyze market trends")
)
session_info = client.session.get_info(session.session_id)

# Execute AI task
ws_client = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key,
    session_id=session_info.session_id
)
task_runner = ws_client.create_task_runner(client, session_info)

result = task_runner.run_task(
    task="Analyze Q4 2024 market trends in tech sector",
    team_id="wyse_mate",
    options=TaskExecutionOptions(auto_accept_plan=True)
)

if result.success:
    print(f"✅ Analysis complete: {result.final_answer}")
    print(f"⏱️ Completed in {result.session_duration:.1f} seconds")
else:
    print(f"❌ Task failed: {result.error}")
```

**🎯 [Complete Quick Start Guide →](./examples/quickstart.md)**

## 🎮 Key Features

### 🤖 Simplified Task Execution

Execute complex AI workflows with minimal code:

```python
# Automated execution - fire and forget
result = task_runner.run_task(
    task="Create a comprehensive market analysis report",
    team_id="wyse_mate",
    options=TaskExecutionOptions(auto_accept_plan=True)
)

# Interactive execution - with user input
task_runner.run_interactive_session(
    initial_task="Help me research competitors",
    team_id="wyse_mate"
)
```

### 📂 File Upload & Processing

```python
# Upload files for AI analysis
uploaded_files = []
upload_result = client.file_upload.upload_file("data.csv")
if upload_result.get("file_url"):
    uploaded_files.append({
        "file_name": "data.csv",
        "file_url": upload_result["file_url"]
    })

# Use files in task execution
result = task_runner.run_task(
    task="Analyze this dataset and create visualizations",
    attachments=uploaded_files,
    team_id="wyse_mate"
)
```

### ⚡ Real-time WebSocket Integration

```python
from wyseos.mate.websocket import WebSocketClient, MessageType

ws = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key,
    session_id=session_id
)

ws.set_message_handler(lambda msg: print(f"AI Agent: {msg.get('content')}"))
ws.connect(session_id)
```

### 🔧 Flexible Configuration

```yaml
# mate.yaml
mate:
  api_key: "your-api-key"
  base_url: "https://api.wyseos.com"
  timeout: 30
```

```python
# Configuration options
options = TaskExecutionOptions(
    auto_accept_plan=True,           # ✅ Auto-approve AI plans
    capture_screenshots=False,        # 📸 Browser screenshots
    enable_browser_logging=True,      # 🌐 Browser activity logs
    completion_timeout=300,           # ⏱️ Task timeout
)
```

## 📚 Documentation & Examples

| Resource | Description |
|----------|-------------|
| **[🚀 Quick Start Guide](./examples/quickstart.md)** | Get up and running in 5 minutes |
| **[📖 Installation Guide](./installation.md)** | Detailed installation instructions |
| **[🎯 Complete Example](./examples/getting_started/example.py)** | Full-featured example application |
| **[📋 Release Notes](./RELEASES.md)** | Latest updates and changes |

### 🎪 Example Applications

The `examples/` directory contains real-world usage patterns:

- **📊 Data Analysis**: Upload CSV files and get AI-powered insights
- **🌐 Web Research**: Automated web browsing and data extraction  
- **📝 Document Processing**: Analyze PDFs, images, and text files
- **💬 Interactive Sessions**: Build chatbot-like experiences
- **🔄 Workflow Automation**: Chain multiple AI tasks together

## 🛠️ Development & Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/WyseOS/wyseos-sdk-python
cd wyseos-sdk-python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e .

# Install development tools (optional)
pip install pytest pytest-cov black isort flake8 mypy
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=wyseos
```

### Contributing

We welcome contributions! Please:

1. 🍴 Fork the repository
2. 🌿 Create a feature branch (`git checkout -b feature/amazing-feature`)
3. 💾 Commit your changes (`git commit -m 'Add amazing feature'`)
4. 📤 Push to the branch (`git push origin feature/amazing-feature`)
5. 🔄 Open a Pull Request

## 📊 Project Status

| Component | Status |
|-----------|--------|
| 🔧 Core SDK | ✅ Complete |
| 🌐 WebSocket Support | ✅ Complete |
| 📁 File Upload | ✅ Complete |
| 🤖 Task Execution | ✅ Complete |
| 📚 Documentation | ✅ Complete |
| 🧪 Test Coverage | 🚧 In Progress |
| 📱 Mobile Examples | 📋 Planned |

## 🏗️ Architecture

```
wyseos/
├── mate/                    # Core SDK module
│   ├── client.py           # Main API client
│   ├── websocket.py        # WebSocket + TaskRunner
│   ├── models.py           # Pydantic data models
│   ├── config.py           # Configuration management
│   ├── errors.py           # Exception classes
│   └── services/           # API service modules
│       ├── user.py         # User management
│       ├── team.py         # Team operations
│       ├── agent.py        # AI agent management
│       ├── session.py      # Session handling
│       ├── browser.py      # Browser automation
│       └── file_upload.py  # File operations
```

## 🔗 API Reference

### Core Classes

| Class | Purpose |
|-------|---------|
| `Client` | Main API client for HTTP requests |
| `WebSocketClient` | Real-time WebSocket communication |
| `TaskRunner` | Simplified task execution interface |
| `TaskExecutionOptions` | Configuration for task execution |
| `TaskResult` | Comprehensive task execution results |

### Key Methods

```python
# Client operations
client.user.list_api_keys()
client.team.get_list()
client.agent.get_list()
client.session.create()

# File operations
client.file_upload.validate_file()
client.file_upload.upload_file()

# Task execution
task_runner.run_task()              # Automated execution
task_runner.run_interactive_session()  # Interactive mode
```

## 🚨 Error Handling

The SDK provides structured error handling:

```python
from wyseos.mate.errors import APIError, ValidationError, NetworkError

try:
    result = task_runner.run_task("Your task")
except ValidationError as e:
    print(f"Validation error: {e}")
except APIError as e:
    print(f"API error: {e.message}")
except NetworkError as e:
    print(f"Network error: {e}")
```

## 🌟 What's New in v0.2.0

- 🎯 **New TaskRunner Interface**: Execute AI tasks with 90% less code
- ⚡ **Performance Optimizations**: Screenshots disabled by default for faster execution
- 🔧 **Simplified Configuration**: Cleaner options with intelligent defaults
- 📚 **Enhanced Documentation**: Complete rewrite with practical examples
- 🏗️ **Improved Architecture**: Better separation of concerns and modularity

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Community

- 🐛 **Issues**: [GitHub Issues](https://github.com/WyseOS/wyseos-sdk-python/issues)
- 📧 **Email**: support@wyseos.com
- 💬 **Discussions**: [GitHub Discussions](https://github.com/WyseOS/wyseos-sdk-python/discussions)
- 📖 **Documentation**: [API Docs](https://docs.wyseos.com)

## 🔗 Related Projects

- 🌐 **WyseOS Platform**: [wyseos.com](https://wyseos.com)
- 📦 **PyPI Package**: [pypi.org/project/wyseos-sdk](https://pypi.org/project/wyseos-sdk/)
- 🧪 **JavaScript SDK**: Coming soon
- 🔗 **REST API**: [docs.wyseos.com](https://docs.wyseos.com)

---

<div align="center">

**🚀 Ready to build the future with AI?**

[Get Started](./examples/quickstart.md) • [View Examples](./examples/) • [API Docs](https://docs.wyseos.com)

Built with ❤️ by the WyseOS team

</div>