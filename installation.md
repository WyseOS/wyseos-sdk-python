[English](installation.md) | [中文](installation_cn.md)

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
```

Activate the virtual environment:

- macOS/Linux:

```bash
source .venv/bin/activate
```

- Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies and the local package:

```bash
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

## Client Initialization

```python
from wyseos.mate import Client, ClientOptions

client = Client(ClientOptions(
    api_key="your-api-key",             # or jwt_token="your-jwt-token" (pick one)
    base_url="https://api.wyseos.com",  # required
    timeout=30,                         # optional, default 30s
))
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
