# Installation Guide

Install and configure the WyseOS Python SDK for the latest session protocol.

## Requirements

- Python 3.9+
- macOS, Linux, or Windows

## Install from PyPI

```bash
pip install wyseos-sdk
```

## Install from Source

```bash
git clone https://github.com/WyseOS/wyseos-sdk-python
cd wyseos-sdk-python
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Basic Verification

```python
from wyseos.mate import Client, ClientOptions

client = Client(ClientOptions(api_key="your-api-key"))
print("SDK loaded, base_url:", client.base_url)
```

## Configuration

Create `mate.yaml`:

```yaml
mate:
  # Use one of api_key or jwt_token
  api_key: "your-api-key"
  # jwt_token: "your-jwt-token"

  base_url: "https://api.wyseos.com"
  timeout: 30
```

Load config:

```python
from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config

try:
    client = Client(load_config("mate.yaml"))
except Exception:
    client = Client(ClientOptions(api_key="your-api-key"))
```

## Authentication Notes

- HTTP:
  - `api_key` -> `x-api-key`
  - `jwt_token` -> `Authorization` (no `Bearer ` prefix)
- WebSocket:
  - API Key query: `?api_key=...`
  - JWT query: `?authorization=...`

## Next

- Quick Start: `examples/quickstart.md`
- Protocol Spec: `docs/wyse-session-protocol.md`
- Full Example: `examples/getting_started/example.py`
