# Quick Start Guide

Get up and running with the WyseOS SDK for Python in minutes.

## Set Up a Virtual Environment (Recommended)

Before installing the SDK, it's a good practice to create a virtual environment to isolate project dependencies.

### Using `venv`

```bash
# Create the environment
python -m venv wyseos-sdk-env

# Activate it
# On macOS/Linux:
source wyseos-sdk-env/bin/activate
# On Windows:
# .\wyseos-sdk-env\Scripts\activate
```

### Using `conda`

```bash
# Create and activate the environment
conda create -n wyseos-sdk python=3.9
conda activate wyseos-sdk
```

## 1. Installation

Once your virtual environment is activated, install the SDK:

```bash
pip install wyseos-sdk
```

## 2. Get Your API Key

1. Sign up at [mate.wyseos.com](https://mate.wyseos.com)
2. Create an API key in your dashboard
3. Keep it secure

## 3. Configure

This quick start example includes a `mate.yaml` file. Open `examples/getting_started/mate.yaml` and add your API key.

The configuration file should look like this:

```yaml
mate:
  api_key: "your-api-key"
  base_url: "https://api.mate.wyseos.com"
  timeout: 30
```

## 4. Initialize the Client

To run the examples, the client needs to load the configuration file from its specific path.

```python
import os
from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Build the path to the config file
config_path = os.path.join(script_dir, "mate.yaml")

try:
    # Load configuration from the specific path
    client = Client(load_config(config_path))
except Exception:
    # Fallback to manual options if config fails
    client = Client(ClientOptions(api_key="your-api-key"))
```

## 5. First Calls

### List API Keys
```python
from wyseos.mate.models import ListOptions

api_keys = client.user.list_api_keys(ListOptions(page_num=1, page_size=10))
print(f"Found {api_keys.total} API keys")
for key in api_keys.data:
    print(f"- {key.name}")
```

### List Teams
```python
from wyseos.mate.models import ListOptions

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
from wyseos.mate.models import CreateSessionRequest

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
from wyseos.mate.models import ListOptions

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
from wyseos.mate.websocket import WebSocketClient, MessageType

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
from wyseos.mate.errors import APIError, ValidationError, NetworkError, ConfigError

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
from wyseos.mate.models import ListOptions

opts = ListOptions(page_num=1, page_size=10)
page = client.team.get_list(options=opts)

all_teams = list(page.data)
while opts.page_num * opts.page_size < page.total:
    opts.page_num += 1
    page = client.team.get_list(options=opts)
    all_teams.extend(page.data)
```

—

- **Docs**: `../README.md`
- **Install Guide**: `../installation.md`