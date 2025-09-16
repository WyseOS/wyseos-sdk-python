# 🚀 Quick Start Guide

Get up and running with the WyseOS SDK for Python in minutes.

## 📋 Table of Contents

- [🔧 Setup](#setup)
- [🔑 Configuration](#configuration)
- [⚡ Quick Examples](#quick-examples)
- [🤖 Task Execution](#task-execution)
- [🔄 Real-time WebSocket](#real-time-websocket)
- [📂 File Uploads](#file-uploads)
- [⚠️ Error Handling](#error-handling)

## 🔧 Setup

### 1. Create Virtual Environment (Recommended)

```bash
# Using venv
python -m venv wyseos-sdk-env
source wyseos-sdk-env/bin/activate  # macOS/Linux
# .\wyseos-sdk-env\Scripts\activate  # Windows

# Using conda
conda create -n wyseos-sdk python=3.9
conda activate wyseos-sdk
```

### 2. Install SDK

```bash
pip install wyseos-sdk
```

## 🔑 Configuration

### Get Your API Key
1. 🌐 Sign up at [mate.wyseos.com](https://mate.wyseos.com)
2. 🔐 Create an API key in your dashboard
3. 💾 Save it securely

### Configuration File

Create `mate.yaml` in your project directory:

```yaml
mate:
  api_key: "your-api-key"
  base_url: "https://api.wyseos.com"
  timeout: 30
```

### Initialize Client

```python
import os
from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config

# Load from config file
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mate.yaml")
    client = Client(load_config(config_path))
    print("✅ Configuration loaded successfully")
except Exception as e:
    # Fallback to manual configuration
    client = Client(ClientOptions(api_key="your-api-key"))
    print("⚠️ Using fallback configuration")
```

## ⚡ Quick Examples

### 📊 List Resources

```python
from wyseos.mate.models import ListOptions

# List API keys
api_keys = client.user.list_api_keys(ListOptions(page_num=1, page_size=10))
print(f"🔑 Found {api_keys.total} API keys")

# List teams
teams = client.team.get_list("wyse_mate", ListOptions(page_num=1, page_size=10))
print(f"👥 Found {teams.total} teams")

# List agents
agents = client.agent.get_list("all", ListOptions(page_num=1, page_size=10))
print(f"🤖 Found {agents.total} agents")
```

### 🎯 Create Session

```python
from wyseos.mate.models import CreateSessionRequest

# Create a new session
session_resp = client.session.create(
    CreateSessionRequest(team_id="wyse_mate", task="Analyze this document")
)
session_info = client.session.get_info(session_resp.session_id)
print(f"📋 Created session: {session_resp.session_id}")
print(f"📊 Status: {session_info.status}")
```

## 🤖 Task Execution

The SDK provides two execution modes:

### 🎯 Automated Task Execution

Perfect for fire-and-forget tasks:

```python
from wyseos.mate.websocket import WebSocketClient, TaskExecutionOptions

# Setup WebSocket client
ws_client = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key,
    session_id=session_info.session_id
)

# Create task runner
task_runner = ws_client.create_task_runner(client, session_info)

# Configure execution options
options = TaskExecutionOptions(
    auto_accept_plan=True,
    capture_screenshots=False,  # Performance optimized
    enable_browser_logging=True,
    completion_timeout=300  # 5 minutes
)

# Run task
result = task_runner.run_task(
    task="Analyze this data and provide insights",
    team_id=session_info.team_id,
    options=options
)

# Check results
if result.success:
    print("✅ Task completed!")
    print(f"📝 Answer: {result.final_answer}")
    print(f"⏱️ Duration: {result.session_duration:.1f}s")
    print(f"📊 Messages: {result.message_count}")
else:
    print(f"❌ Task failed: {result.error}")
```

### 💬 Interactive Session

For tasks requiring user interaction:

```python
# Configure for interactive use
options = TaskExecutionOptions(
    auto_accept_plan=True,
    capture_screenshots=True,  # Enable for visual tasks
    completion_timeout=600  # 10 minutes
)

# Start interactive session
task_runner.run_interactive_session(
    initial_task="Help me research this topic",
    team_id=session_info.team_id,
    options=options
)

# Session will prompt for user input
# Type 'exit', 'quit', or 'q' to end
# Type 'stop' to halt current task
```

## 🔄 Real-time WebSocket

### Basic WebSocket Usage

```python
from wyseos.mate.websocket import WebSocketClient, MessageType

# Create WebSocket connection
ws = WebSocketClient(
    base_url=client.base_url,
    api_key=client.api_key,
    session_id=session_info.session_id
)

# Setup handlers
ws.set_connect_handler(lambda: print("🔗 WebSocket connected"))
ws.set_disconnect_handler(lambda: print("🔌 WebSocket disconnected"))
ws.set_message_handler(lambda msg: print(f"📨 Received: {msg.get('type', 'unknown')}"))

# Connect and start task
ws.connect(session_info.session_id)

# Send start message
start_message = {
    "type": MessageType.START,
    "data": {
        "messages": [{"type": "task", "content": "Your task here"}],
        "attachments": [],
        "team_id": session_info.team_id,
        "kb_ids": []
    }
}
ws.send_message(start_message)

# Remember to disconnect
ws.disconnect()
```

## 📂 File Uploads

### Upload Files for Task Execution

```python
# Validate and upload files
uploaded_files = []
file_paths = ["document.pdf", "data.csv", "image.png"]

for file_path in file_paths:
    # Validate file
    is_valid, message = client.file_upload.validate_file(file_path)
    if is_valid:
        print(f"✅ Validation passed: {file_path}")
        
        # Upload file
        upload_result = client.file_upload.upload_file(file_path)
        if upload_result.get("file_url"):
            file_info = client.file_upload.get_file_info(file_path)
            uploaded_files.append({
                "file_name": file_info["name"],
                "file_url": upload_result["file_url"]
            })
            print(f"📤 Uploaded: {file_info['name']}")
        else:
            print(f"❌ Upload failed: {upload_result.get('error')}")
    else:
        print(f"❌ Validation failed: {message}")

# Use files in task execution
result = task_runner.run_task(
    task="Analyze these uploaded files",
    team_id=session_info.team_id,
    attachments=uploaded_files,
    options=options
)
```

## ⚠️ Error Handling

### Comprehensive Error Handling

```python
from wyseos.mate.errors import APIError, ValidationError, NetworkError, ConfigError

try:
    # Your SDK operations here
    result = task_runner.run_task(
        task="Your task",
        team_id="wyse_mate",
        options=TaskExecutionOptions()
    )
    
except ValidationError as e:
    print(f"🔍 Validation error: {e}")
except APIError as e:
    status = getattr(e, 'status_code', 'unknown')
    print(f"🌐 API error [{status}]: {e.message}")
except NetworkError as e:
    print(f"📡 Network error: {e}")
except ConfigError as e:
    print(f"⚙️ Configuration error: {e}")
except Exception as e:
    print(f"💥 Unexpected error: {e}")
```

### Task Execution Error Handling

```python
# Check task results
if result.success:
    print(f"✅ Success: {result.final_answer}")
else:
    print(f"❌ Failed: {result.error}")
    
    # Access execution details
    if result.execution_logs:
        print(f"📋 Logs: {len(result.execution_logs)} entries")
    
    if result.screenshots:
        print(f"📸 Screenshots: {len(result.screenshots)} captured")
```

## 🔧 Configuration Options

### TaskExecutionOptions

```python
from wyseos.mate.websocket import TaskExecutionOptions

options = TaskExecutionOptions(
    auto_accept_plan=True,           # ✅ Auto-accept execution plans
    capture_screenshots=False,        # 📸 Capture browser screenshots
    enable_browser_logging=True,      # 🌐 Log browser activities  
    enable_event_logging=True,        # 📝 Detailed execution logs
    completion_timeout=300,           # ⏱️ Timeout in seconds
    max_user_input_timeout=0          # ⌛ User input timeout (0 = infinite)
)
```

## 🔗 Complete Example

```python
#!/usr/bin/env python3
import os
from wyseos.mate import Client
from wyseos.mate.config import load_config
from wyseos.mate.models import CreateSessionRequest
from wyseos.mate.websocket import WebSocketClient, TaskExecutionOptions

def main():
    # 1. Initialize client
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mate.yaml")
    client = Client(load_config(config_path))
    
    # 2. Create session
    session_resp = client.session.create(
        CreateSessionRequest(team_id="wyse_mate", task="My task")
    )
    session_info = client.session.get_info(session_resp.session_id)
    
    # 3. Setup task execution
    ws_client = WebSocketClient(
        base_url=client.base_url,
        api_key=client.api_key,
        session_id=session_info.session_id
    )
    task_runner = ws_client.create_task_runner(client, session_info)
    
    # 4. Run task
    result = task_runner.run_task(
        task="Analyze market trends for Q4 2024",
        team_id=session_info.team_id,
        options=TaskExecutionOptions(auto_accept_plan=True)
    )
    
    # 5. Display results
    if result.success:
        print(f"✅ {result.final_answer}")
    else:
        print(f"❌ {result.error}")

if __name__ == "__main__":
    main()
```

---

## 📚 Next Steps

- 📖 **Full Documentation**: `../README.md`
- 🛠️ **Installation Guide**: `../installation.md`  
- 🎯 **Complete Examples**: `getting_started/example.py`
- 🐛 **Issues & Support**: [GitHub Issues](https://github.com/wyseos/wyseos-sdk-python/issues)

---

**🎉 You're ready to build amazing AI-powered applications with WyseOS!**