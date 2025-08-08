# Mate SDK Python 

[![Python SDK CI/CD](https://github.com/WyseOS/mate-sdk-python/actions/workflows/python-sdk-ci.yml/badge.svg)](https://github.com/WyseOS/mate-sdk-python/actions/workflows/python-sdk-ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![PyPI Package](https://img.shields.io/badge/PyPI-wyse--mate--sdk-blue)](https://pypi.org/project/wyse-mate-sdk/)
[![Documentation](https://img.shields.io/badge/docs-comprehensive-green)](./README.md)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Mate SDK Python for interacting with the Mate API. Built with modern Python practices, type safety, and real-time support.

## 🚀 Features

- **🎯 Type Safe**: Pydantic models and validation
- **⚡ Real-time**: WebSocket client
- **🔧 Simple Config**: YAML config file support
- **🛡️ Robust Errors**: Clear, structured exceptions

## 📦 Installation

```bash
pip install wyse-mate-sdk
```

## 🏃‍♂️ Quick Start

```python
from wyse_mate import Client, ClientOptions
from wyse_mate.config import load_config

# Initialize using mate.yaml (in CWD)
client = Client(load_config())

# List teams
from wyse_mate.models import ListOptions
teams = client.team.get_list(options=ListOptions(page_num=1, page_size=10))
print(f"Found {teams.total} teams")

# Create a session and read messages
from wyse_mate.models import CreateSessionRequest
session = client.session.create(CreateSessionRequest(team_id="your-team-id", task="My task"))
info = client.session.get_info(session.session_id)
msgs = client.session.get_messages(session.session_id, page_num=1, page_size=20)
print(info.status, msgs.total_count)

# WebSocket (Real Time)
from wyse_mate.websocket import WebSocketClient
ws = WebSocketClient(base_url=client.base_url, api_key=client.api_key, session_id=info.session_id)
ws.set_message_handler(lambda m: print(m))
ws.connect(info.session_id)
```

## 📚 Documentation

- **[Installation Guide](./installation.md)**
- **[Quick Start Guide](./quickstart.md)**

## 🔧 Configuration

Create `mate.yaml`:

```yaml
api_key: "your-api-key"
base_url: "https://api.mate.wyseos.com"
timeout: 30
debug: false
```

Load configuration:

```python
from wyse_mate import Client
from wyse_mate.config import load_config

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
from wyse_mate.websocket import WebSocketClient, MessageType

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
git clone https://github.com/WyseOS/mate-sdk-python
cd mate-sdk-python

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

- Issues: https://github.com/WyseOS/mate-sdk-python/issues
- Email: support@wyseos.com

## 🔗 Links

- PyPI: https://pypi.org/project/wyse-mate-sdk/
- API Docs: https://docs.wyseos.com
- Website: https://wyseos.com

—

Ready for production. Build with Mate SDK Python.