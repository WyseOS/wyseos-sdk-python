# Installation Guide

Install and set up the Mate SDK Python.

## Requirements

- Python 3.9+
- Windows, macOS, or Linux

## Install

```bash
pip install wyse-mate-sdk
```

## From Source

```bash
git clone https://github.com/WyseOS/mate-sdk-python
cd mate-sdk-python
pip install -e .
```

## Verify

```python
import wyse_mate
from wyse_mate import Client
from wyse_mate.config import load_config

print(f"Mate SDK Python version: {wyse_mate.__version__}")
client = Client(load_config())
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
api_key: "your-api-key"
base_url: "https://api.mate.wyseos.com"
timeout: 30
debug: false
```

Load configuration:

```python
from wyse_mate import Client, ClientOptions
from wyse_mate.config import load_config

try:
    client = Client(load_config())
except Exception:
    client = Client(ClientOptions(api_key="your-api-key"))
```

## Virtual Environment (Recommended)

### venv

```bash
python -m venv mate-sdk-env
# macOS/Linux
source mate-sdk-env/bin/activate
# Windows
# mate-sdk-env\Scripts\activate
pip install wyse-mate-sdk
```

### conda

```bash
conda create -n mate-sdk python=3.9
conda activate mate-sdk
pip install wyse-mate-sdk
```

## Troubleshooting

- **ImportError: No module named 'wyse_mate'**: Ensure the environment is activated and the package is installed.
- **ConfigError: Configuration file not found: mate.yaml**: Create `mate.yaml` or pass a custom path to `load_config`.
- **SSLCertificateError**: Update certificates or configure SSL appropriately in your environment.
- **Invalid YAML**: Ensure proper YAML syntax and indentation.

## Getting Help

- Issues: https://github.com/WyseOS/mate-sdk-python/issues
- Docs: `README.md`
- Support: info@wyseos.com 