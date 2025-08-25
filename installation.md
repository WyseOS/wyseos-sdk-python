# Installation Guide

Install and set up the Mate SDK Python.

## Requirements

- Python 3.9+
- Windows, macOS, or Linux

## Install

```bash
pip install wyseos-sdk
```

## From Source

```bash
git clone https://github.com/WyseOS/wyseos-sdk-python
cd wyseos-sdk-python
pip install -e .
```

## Verify

```python
import wyseos.mate

print(f"WyseOS SDK Python version: {wyseos.mate.__version__}")
print("✅ Installation successful!")
```

## Dependencies

Automatically installed:

- requests ≥ 2.31.0
- pydantic ≥ 2.0.0
- websockets ≥ 11.0.0
- PyYAML ≥ 6.0.0

## Configuration

Create `mate.yaml` in your project root:

```yaml
mate:
  api_key: "your-api-key"
  base_url: "https://api.mate.wyseos.com"
  timeout: 30
```

Load configuration:

```python
from wyseos.mate import Client, ClientOptions
from wyseos.mate.config import load_config

try:
    client = Client(load_config())
except Exception:
    client = Client(ClientOptions(api_key="your-api-key"))
```

## Virtual Environment (Recommended)

### venv

```bash
python -m venv wyseos-sdk-env
# macOS/Linux
source wyseos-sdk-env/bin/activate
# Windows
# wyseos-sdk-env\Scripts\activate
pip install wyseos-sdk
```

### conda

```bash
conda create -n wyseos-sdk python=3.9
conda activate wyseos-sdk
pip install wyseos-sdk
```

## Troubleshooting

- **ImportError: No module named 'wyseos.mate'**: Ensure the environment is activated and the package is installed.
- **ConfigError: Configuration file not found: mate.yaml**: Create `mate.yaml` or pass a custom path to `load_config`.
- **SSLCertificateError**: Update certificates or configure SSL appropriately in your environment.
- **Invalid YAML**: Ensure proper YAML syntax and indentation.

## Getting Help

- Issues: https://github.com/WyseOS/wyseos-sdk-python/issues
- Docs: `README.md`
- Support: info@wyseos.com 