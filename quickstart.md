# Quick Start Guide

Get up and running with the Mate SDK Python in minutes.

## 1. Installation

```bash
pip install wyse-mate-sdk
```

## 2. Get Your API Key

1. Sign up at [mate.wyseos.com](https://mate.wyseos.com)
2. Create an API key in your dashboard
3. Keep it secure

## 3. Configure

Create a `mate.yaml` in your project root:

```yaml
api_key: "your-api-key"
base_url: "https://api.mate.wyseos.com"
timeout: 30
debug: false
```

## 4. Initialize the Client

```python
from wyse_mate import Client, ClientOptions
from wyse_mate.config import load_config

# Prefer config file (mate.yaml)
try:
    client = Client(load_config())
except Exception:
    # Fallback to manual options
    client = Client(ClientOptions(api_key="your-api-key"))
```

## 5. First Calls

### List API Keys
```python
from wyse_mate.models import ListOptions

api_keys = client.user.list_api_keys(ListOptions(page_num=1, page_size=10))
print(f"Found {api_keys.total} API keys")
for key in api_keys.data:
    print(f"- {key.name}")
```

### List Teams
```python
from wyse_mate.models import ListOptions

teams = client.team.get_list(team_type="wyse_mate", options=ListOptions(page_num=1, page_size=10))
print(f"Found {teams.total} teams")
for team in teams.data:
    print(f"- {team.name} (ID: {team.team_id})")
```

### Team Details
```python
if teams.data:
    team_info = client.team.get_info(teams.data[0].team_id)
    print(f"Team type: {team_info.team_type}")
```

### List Agents
```python
agents = client.agent.get_list(agent_type="coder", options=ListOptions(page_num=1, page_size=10))
print(f"Found {agents.total} agents")
for agent in agents.data:
    print(f"- {agent.name} (Type: {agent.agent_type})")
```

## 6. Sessions

Create a session and fetch messages.

```python
from wyse_mate.models import CreateSessionRequest

# Create
session_resp = client.session.create(
    CreateSessionRequest(team_id="your-team-id", task="My first task")
)
print(f"Created session: {session_resp.session_id}")

# Read info
session_info = client.session.get_info(session_resp.session_id)
print(f"Session status: {session_info.status}")

# Messages (paginated)
msgs = client.session.get_messages(session_resp.session_id, page_num=1, page_size=20)
print(f"Total messages: {msgs.total_count}")
```

## 7. Browser

```python
# List browsers for a session
from wyse_mate.models import ListOptions

browsers = client.browser.list_browsers(session_id=session_resp.session_id, options=ListOptions(page_num=1, page_size=10))
print(f"Found {browsers.total} browsers")

if browsers.browsers:
    b = browsers.browsers[0]
    info = client.browser.get_info(b.browser_id)
    print(f"Browser status: {info.status}")

    # List pages
    pages = client.browser.list_browser_pages(b.browser_id, options=ListOptions(page_num=1, page_size=10))
    print(f"Browser pages: {pages.total}")
```

## 8. WebSocket (Real-time)

```python
from wyse_mate.websocket import WebSocketClient, MessageType

ws = WebSocketClient(
    base_url=client.base_url,  # e.g., https://api.mate.wyseos.com
    api_key=client.api_key,
    session_id=session_resp.session_id,
)

ws.set_connect_handler(lambda: print("WebSocket connected"))
ws.set_disconnect_handler(lambda: print("WebSocket disconnected"))
ws.set_message_handler(lambda m: print(f"Received: {m}"))

# Connect
ws.connect(session_resp.session_id)

# Start a task via WebSocket (optional)
start_msg = {
    "type": MessageType.START,
    "data": {
        "messages": [{"type": "task", "content": "Do something"}],
        "attachments": [],
        "team_id": session_info.team_id,
        "kb_ids": [],
    },
}
ws.send_message(start_msg)

# When done
ws.disconnect()
```

## 9. Error Handling

```python
from wyse_mate.errors import APIError, ValidationError, NetworkError, ConfigError

try:
    teams = client.team.get_list()
except ValidationError as e:
    print(f"Validation error: {e}")
except APIError as e:
    print(f"API error {e.status_code if hasattr(e, 'status_code') else ''}: {e.message}")
except NetworkError as e:
    print(f"Network error: {e}")
except ConfigError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## 10. Pagination Pattern

```python
from wyse_mate.models import ListOptions

opts = ListOptions(page_num=1, page_size=10)
page = client.team.get_list(options=opts)

all_teams = list(page.data)
while opts.page_num * opts.page_size < page.total:
    opts.page_num += 1
    page = client.team.get_list(options=opts)
    all_teams.extend(page.data)
```

—

- **Docs**: `README.md`
- **Install Guide**: `installation.md`