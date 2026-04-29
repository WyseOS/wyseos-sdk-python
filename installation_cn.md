[English](installation.md) | [中文](installation_cn.md)

# 安装指南

安装并配置 OctoEvo Python SDK，以使用最新会话协议。

## 环境要求

- Python 3.9+
- macOS、Linux 或 Windows

## 从 PyPI 安装

```bash
pip install octoevo
```

## 从源码安装

```bash
git clone https://github.com/WyseOS/wyseos-sdk-python
cd wyseos-sdk-python
python -m venv .venv
```

激活虚拟环境：

- macOS/Linux：

```bash
source .venv/bin/activate
```

- Windows（PowerShell）：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装依赖并安装本地包：

```bash
pip install -e .
```

## 基础验证

```python
from octoevo.mate import Client, ClientOptions

client = Client(ClientOptions(api_key="your-api-key"))
print("SDK loaded, base_url:", client.base_url)
```

## 配置

创建 `mate.yaml`：

```yaml
mate:
  # Use one of api_key or jwt_token
  api_key: "your-api-key"
  # jwt_token: "your-jwt-token"

  base_url: "https://api.dev.weclaw.ai"
  timeout: 30
```

## 客户端初始化

```python
from octoevo.mate import Client, ClientOptions

client = Client(ClientOptions(
    api_key="your-api-key",             # or jwt_token="your-jwt-token" (pick one)
    base_url="https://api.dev.weclaw.ai",  # required
    timeout=30,                         # optional, default 30s
))
```

## 认证说明

- HTTP：
  - `api_key` -> `x-api-key`
  - `jwt_token` -> `Authorization`（不带 `Bearer ` 前缀）
- WebSocket：
  - API Key query: `?api_key=...`
  - JWT query: `?authorization=...`

## 下一步

- 快速开始：`examples/quickstart.md`
- 协议规范：`docs/wyse-session-protocol.md`
- 完整示例：`examples/getting_started/example.py`
