# Quick Start Guide

Get up and running with the Mate SDK Python in minutes!

## 1. Installation

```bash
pip install wyse-mate-sdk
```

## 2. Get Your API Key

1. Sign up for a Wyse Mate account at [mate.wyseos.com](https://mate.wyseos.com)
2. Go to your dashboard and create an API key
3. Save your API key securely

## 3. Basic Setup

### Configuration File (Recommended)

Create a `mate.yaml` file in your project root:

```yaml
api_key: "your-api-key-here"
base_url: "https://api.mate.wyseos.com"
timeout: 30
debug: false
```

### Python Code

```python
from wyse_mate import Client
from wyse_mate.config import load_default_config

# Load configuration from mate.yaml
config = load_default_config()
if config:
    client = Client(config)
else:
    # Fallback to manual configuration
    from wyse_mate import ClientOptions
    client = Client(ClientOptions(
        api_key="your-api-key-here"
    ))
```

## 4. Your First API Call

Let's list your teams:

```python
# List all teams
teams_response = client.team.get_list()
print(f"You have {teams_response.total_count} teams")

for team in teams_response.teams:
    print(f"- {team.name} (ID: {team.team_id})")
```

## 5. Complete Example: Basic API Usage

Here's a complete example that demonstrates the main SDK features:

```python
from wyse_mate import Client, ClientOptions
from wyse_mate.config import load_default_config
from wyse_mate.models import ListOptions

def main():
    # Initialize client
    try:
        config = load_default_config()
        if config:
            client = Client(config)
        else:
            client = Client(ClientOptions(
                api_key="your-api-key-here",
                base_url="https://api.mate.wyseos.com"
            ))
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return

    try:
        # 1. List your API keys
        print("📋 Fetching your API keys...")
        api_keys_response = client.user.list_api_keys()
        print(f"✅ Found {api_keys_response.total_count} API keys")

        # 2. List your teams
        print("📋 Fetching your teams...")
        teams_response = client.team.get_list()
        
        if not teams_response.teams:
            print("❌ No teams found.")
            return
        
        team = teams_response.teams[0]  # Use first team
        print(f"✅ Using team: {team.name}")

        # 3. Get team details
        print("🔍 Getting team details...")
        team_details = client.team.get_info(team.team_id)
        print(f"✅ Team type: {team_details.team_type}")

        # 4. List agents
        print("🤖 Fetching agents...")
        agents_response = client.agent.get_list()
        print(f"✅ Found {agents_response.total_count} agents")

        # 5. List existing sessions
        print("📜 Fetching sessions...")
        sessions_response = client.session.list_sessions()
        print(f"✅ Found {sessions_response.total_count} sessions")

        if sessions_response.sessions:
            session = sessions_response.sessions[0]
            print(f"📊 Session: {session.session_id}")
            
            # Get session messages
            messages = client.session.get_messages(session.session_id)
            print(f"💬 Session has {messages.total_count} messages")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
```

## 6. Working with Different Services

### User Management

```python
from wyse_mate.models import ListOptions

# List API keys with pagination
api_keys = client.user.list_api_keys(
    ListOptions(page=1, page_size=10)
)
print(f"Found {api_keys.total_count} API keys")

for key in api_keys.api_keys:
    print(f"- {key.name} (ID: {key.id})")
```

### Team Management

```python
# List teams by type
teams = client.team.get_list(team_type="wyse_mate")
print(f"Found {teams.total_count} teams")

# Get specific team details
if teams.teams:
    team_details = client.team.get_info(teams.teams[0].team_id)
    print(f"Team: {team_details.name}")
    print(f"Description: {team_details.description}")
```

### Agent Management

```python
# List agents by type
agents = client.agent.get_list(agent_type="coder")
print(f"Found {agents.total_count} agents")

# Get specific agent details
if agents.agents:
    agent_details = client.agent.get_info(agents.agents[0].agent_id)
    print(f"Agent: {agent_details.name}")
    print(f"Type: {agent_details.agent_type}")
```

### Session Management

```python
from wyse_mate.models import CreateSessionRequest

# Create a new session
session_request = CreateSessionRequest(
    team_id="your-team-id",
    title="My Session"
)
session_response = client.session.create(session_request)
session = session_response.session

# Get session details
session_details = client.session.get_info(session.session_id)
print(f"Session status: {session_details.status}")

# List all sessions
sessions = client.session.list_sessions()
print(f"Total sessions: {sessions.total_count}")
```

### Browser Management

```python
# List browsers
browsers = client.browser.list_browsers()
print(f"Found {browsers.total} browsers")

if browsers.browsers:
    browser = browsers.browsers[0]
    
    # Get browser details
    browser_details = client.browser.get_info(browser.browser_id)
    print(f"Browser status: {browser_details.status}")
    
    # List browser pages
    pages = client.browser.list_browser_pages(browser.browser_id)
    print(f"Browser has {pages.total} pages")
```

### WebSocket Real-time Communication

```python
from wyse_mate.websocket import WebSocketClient

# Create WebSocket client
ws_client = WebSocketClient(
    base_url="wss://api.mate.wyseos.com",
    api_key="your-api-key",
    session_id="your-session-id"
)

# Set up message handler
def on_message(message):
    print(f"Received: {message}")

def on_connect():
    print("WebSocket connected")

def on_disconnect():
    print("WebSocket disconnected")

# Set event handlers
ws_client.set_message_handler(on_message)
ws_client.set_connect_handler(on_connect)
ws_client.set_disconnect_handler(on_disconnect)

# Connect and send message
ws_client.connect()

# Send a message
ws_client.send_message({
    "content": "Hello via WebSocket!",
    "type": "user_message"
})

# Disconnect when done
ws_client.disconnect()
```

## 7. Error Handling

Always handle errors gracefully:

```python
from wyse_mate.errors import APIError, ValidationError, NetworkError, ConfigError

try:
    teams = client.team.get_list()
except ValidationError as e:
    print(f"Validation error: {e.field} - {e.message}")
except APIError as e:
    print(f"API error {e.status_code}: {e.message}")
except NetworkError as e:
    print(f"Network error: {e.message}")
except ConfigError as e:
    print(f"Configuration error: {e.message}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## 8. Configuration Options

### Using Configuration File

Create `mate.yaml`:

```yaml
api_key: "your-api-key"
base_url: "https://api.mate.wyseos.com"
timeout: 30
debug: false
```

Load configuration:

```python
from wyse_mate.config import load_default_config, load_config

# Load from default location (mate.yaml)
config = load_default_config()

# Or load from custom path
config = load_config("custom-config.yaml")

client = Client(config)
```

### Manual Configuration

```python
from wyse_mate import Client, ClientOptions

client = Client(ClientOptions(
    api_key="your-api-key",
    base_url="https://api.mate.wyseos.com",
    timeout=30,
    debug=False
))
```

## 9. Common Patterns

### Pagination

```python
from wyse_mate.models import ListOptions

# Get paginated results
options = ListOptions(page=1, page_size=10)
teams = client.team.get_list(options=options)

# Handle pagination
while teams.pagination and teams.pagination.has_next:
    options.page += 1
    next_teams = client.team.get_list(options=options)
    teams.teams.extend(next_teams.teams)
```

### Error Recovery

```python
from wyse_mate.errors import APIError, NetworkError
import time

def robust_api_call():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return client.team.get_list()
        except NetworkError as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
        except APIError as e:
            if e.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
```

## 10. Next Steps

Now that you're up and running, explore these resources:

- **Full Documentation**: [README.md](./README.md)
- **Installation Guide**: [Installation](installation.md)

## 📞 Need Help?

- **Documentation**: [Full Documentation](./README.md)
- **Email Support**: info@wyseos.com