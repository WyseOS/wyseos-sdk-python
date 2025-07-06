# Installation Guide

This guide walks you through installing and setting up the Mate SDK Python.

## Requirements

- **Python**: 3.9 or higher
- **Operating System**: Windows, macOS, or Linux
- **Dependencies**: All required dependencies are automatically installed

## Installation Methods

### 1. Install from PyPI (Recommended)

```bash
pip install wyse-mate-sdk
```

### 2. Install from Source

```bash
# Clone the repository
git clone https://github.com/wyse/matego.git
cd matego/sdk/python

# Install in development mode
pip install -e .
```

### 3. Install with Poetry

```bash
poetry add wyse-mate-sdk
```

### 4. Install with conda

```bash
conda install -c conda-forge wyse-mate-sdk
```

## Verify Installation

After installation, verify that the SDK is working correctly:

```python
import wyse_mate

# Check version
print(f"Mate SDK Python version: {wyse_mate.__version__}")

# Test basic imports
from wyse_mate import Client, ClientOptions
from wyse_mate.models import TeamInfo
from wyse_mate.errors import APIError

print("✅ Installation successful!")
```

## Dependencies

The SDK automatically installs these dependencies:

- **requests** (≥2.31.0) - HTTP client library
- **pydantic** (≥2.0.0) - Data validation and serialization
- **websockets** (≥11.0.0) - WebSocket client
- **PyYAML** (≥6.0.0) - YAML configuration support

## Virtual Environment (Recommended)

We recommend using a virtual environment to avoid dependency conflicts:

### Using venv

```bash
# Create virtual environment
python -m venv mate-sdk-env

# Activate (Linux/macOS)
source mate-sdk-env/bin/activate

# Activate (Windows)
mate-sdk-env\Scripts\activate

# Install SDK
pip install wyse-mate-sdk
```

### Using conda

```bash
# Create conda environment
conda create -n mate-sdk python=3.9

# Activate environment
conda activate mate-sdk

# Install SDK
pip install wyse-mate-sdk
```

## Development Installation

If you plan to contribute to the SDK or need the latest development version:

```bash
# Clone repository
git clone https://github.com/wyse/matego.git
cd matego/sdk/python

# Install development dependencies
pip install -e ".[dev]"

# Or install manually
pip install -e .
pip install pytest pytest-cov black isort flake8 mypy
```

## Configuration Setup

After installation, you'll need to configure your API credentials:

### Configuration File (Recommended)

Create a `mate.yaml` configuration file in your project root:

```yaml
api_key: "your-api-key-here"
base_url: "https://api.mate.wyseos.com"
timeout: 30
debug: false
```

### Python Code Configuration

```python
from wyse_mate import Client, ClientOptions
from wyse_mate.config import load_default_config

# Method 1: Load from mate.yaml (recommended)
config = load_default_config()
if config:
    client = Client(config)
else:
    print("No mate.yaml found, using manual configuration")
    client = Client(ClientOptions(api_key="your-api-key"))

# Method 2: Manual configuration
client = Client(ClientOptions(
    api_key="your-api-key-here",
    base_url="https://api.mate.wyseos.com",
    timeout=30,
    debug=False
))

# Method 3: Load from custom path
from wyse_mate.config import load_config
config = load_config("custom-config.yaml")
client = Client(config)
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Get started with basic usage

## Troubleshooting

### Common Issues

**Import Error**
```
ImportError: No module named 'wyse_mate'
```
**Solution**: Ensure you've installed the package and activated your virtual environment.

**Configuration Error**
```
ConfigError: Configuration file not found: mate.yaml
```
**Solution**: Create a `mate.yaml` file in your project root or use manual configuration.

**SSL Certificate Error**
```
SSLCertificateError: [SSL: CERTIFICATE_VERIFY_FAILED]
```
**Solution**: Update your certificates or configure SSL verification in ClientOptions.

**Permission Error on Installation**
```
PermissionError: [Errno 13] Permission denied
```
**Solution**: Use `pip install --user wyse-mate-sdk` or use a virtual environment.

**YAML Parse Error**
```
ConfigError: Invalid YAML in configuration file
```
**Solution**: Check your YAML syntax. Use proper indentation and quotes for string values.

### Configuration Validation

The SDK validates your configuration on startup. Common validation errors:

**Missing API Key**
```python
# This will raise a validation error
client = Client(ClientOptions(api_key=""))
```

**Invalid Base URL**
```python
# This will raise a validation error
client = Client(ClientOptions(base_url="invalid-url"))
```

**Invalid Timeout**
```python
# This will raise a validation error
client = Client(ClientOptions(timeout=0))
```

### Getting Help

- [GitHub Issues](https://github.com/wyse/matego/issues)
- [Documentation](./README.md)
- [Support Email](mailto:info@wyseos.com) 