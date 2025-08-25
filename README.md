# WyseOS SDK for Python

[![Python SDK CI/CD](https://github.com/WyseOS/wyseos-sdk-python/actions/workflows/python-sdk-ci.yml/badge.svg)](https://github.com/WyseOS/wyseos-sdk-python/actions/workflows/python-sdk-ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![PyPI Package](https://img.shields.io/badge/PyPI-wyseos--sdk-blue)](https://pypi.org/project/wyseos-sdk/)
[![Documentation](https://img.shields.io/badge/docs-comprehensive-green)](./README.md)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

WyseOS SDK Python for interacting with the WyseOS API. Built with modern Python practices, type safety, and real-time support.

## 🚀 Features

- **🎯 Type Safe**: Pydantic models and validation
- **⚡ Real-time**: WebSocket client
- **🔧 Simple Config**: YAML config file support
- **🛡️ Robust Errors**: Clear, structured exceptions

## 📦 Installation

```bash
pip install wyseos-sdk
```

## 🚀 Examples

To help you get started, we've included a collection of ready-to-run examples in the `examples` directory.

### Getting Started

The `examples/getting_started` directory contains a script demonstrating core features of the SDK. To run it:

1.  Navigate to `examples/getting_started`.
2.  Open `mate.yaml` and add your API key.
3.  Run the script: `python example.py`.

For a more detailed walkthrough, check out the **[Quick Start Guide](./examples/quickstart.md)**.

## 📚 Documentation

- **[Installation Guide](./installation.md)**
- **[Quick Start Guide](./examples/quickstart.md)**

## 🔧 Configuration

Create `mate.yaml`:

```yaml
api_key: "your-api-key"
base_url: "https://api.mate.wyseos.com"
timeout: 30
```

Load configuration:

```python
from wyseos.mate import Client
from wyseos.mate.config import load_config

client = Client(load_config("mate.yaml"))
```

## 🌟 Client Services

- `client.user` — API key management
- `client.team` — Team retrieval
- `client.agent` — Agent retrieval
- `client.session` — Session create/info/messages
- `client.browser` — Browser info/pages/release

## 🧩 Models and Pagination

- `ListOptions(page_num, page_size)`
- Most list endpoints return `PaginatedResponse[T]` with `data`, `total`, `page_num`, `page_size`, `total_page`.

## 🔌 WebSocket

```python
from wyseos.mate.websocket import WebSocketClient, MessageType

ws = WebSocketClient(base_url=client.base_url, api_key=client.api_key, session_id="your-session-id")
ws.set_connect_handler(lambda: print("Connected"))
ws.set_disconnect_handler(lambda: print("Disconnected"))
ws.set_message_handler(lambda m: print(m))
ws.connect("your-session-id")

# Start a task
ws.send_message({
    "type": MessageType.START,
    "data": {
        "messages": [{"type": "task", "content": "Do something"}],
        "attachments": [],
        "team_id": "your-team-id",
        "kb_ids": [],
    },
})
```

## 🛠️ Development

```bash
# Clone repository
git clone https://github.com/WyseOS/wyseos-sdk-python
cd wyseos-sdk-python

# Install in development mode
pip install -e .

# Optional development tools
pip install pytest pytest-cov black isort flake8 mypy
```

## 📊 Project Status

- Core implementation: ✅
- Documentation: ✅
- Tests: 🚧

## 🤝 Contributing

1. Fork
2. Create a branch
3. Commit
4. Push
5. Open a PR

## 📄 License

MIT License — see `LICENSE`.

## 🆘 Support

- Issues: https://github.com/WyseOS/wyseos-sdk-python/issues
- Email: support@wyseos.com

## 🔗 Links

- PyPI: https://pypi.org/project/wyseos-sdk/
- API Docs: https://docs.wyseos.com
- Website: https://wyseos.com

—

Ready for production. Build with WyseOS SDK Python.