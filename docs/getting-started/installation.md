# Installation Guide

This guide covers all installation methods for the Feishu Webhook Bot framework.

## Table of Contents

- [Requirements](#requirements)
- [Installation Methods](#installation-methods)
- [Optional Dependencies](#optional-dependencies)
- [Development Installation](#development-installation)
- [Verification](#verification)
- [Upgrading](#upgrading)
- [Uninstallation](#uninstallation)

## Requirements

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10+ | 3.12+ |
| Memory | 256 MB | 512 MB+ |
| Disk Space | 100 MB | 500 MB+ |
| OS | Windows/Linux/macOS | Linux |

### Python Version

The framework requires Python 3.10 or higher. Check your Python version:

```bash
python --version
# or
python3 --version
```

### Package Manager

We recommend using [uv](https://docs.astral.sh/uv/) for fast, reliable dependency management:

```bash
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

Alternatively, you can use pip or pipx.

## Installation Methods

### Method 1: Using uv (Recommended)

```bash
# Create a new project
mkdir my-feishu-bot && cd my-feishu-bot

# Initialize with uv
uv init

# Add the package
uv add feishu-webhook-bot

# Or install from GitHub
uv add git+https://github.com/AstroAir/feishu-webhook-bot.git
```

### Method 2: Using pip

```bash
# Install from PyPI
pip install feishu-webhook-bot

# Or install from GitHub
pip install git+https://github.com/AstroAir/feishu-webhook-bot.git
```

### Method 3: Using pipx (Isolated Environment)

```bash
# Install pipx if not already installed
pip install pipx
pipx ensurepath

# Install the package
pipx install feishu-webhook-bot
```

### Method 4: From Source

```bash
# Clone the repository
git clone https://github.com/AstroAir/feishu-webhook-bot.git
cd feishu-webhook-bot

# Install with uv
uv sync

# Or install with pip
pip install -e .
```

### Method 5: Docker

```bash
# Pull the image
docker pull ghcr.io/astroair/feishu-webhook-bot:latest

# Run with config file
docker run -v $(pwd)/config.yaml:/app/config.yaml \
  ghcr.io/astroair/feishu-webhook-bot:latest
```

## Optional Dependencies

The framework has optional dependencies for additional features:

### AI Features

```bash
# Using uv
uv add feishu-webhook-bot[ai]

# Using pip
pip install feishu-webhook-bot[ai]
```

Includes:

- `openai` - OpenAI API client
- `anthropic` - Anthropic Claude client
- `google-generativeai` - Google Gemini client

### Web UI

```bash
# Using uv
uv add feishu-webhook-bot[webui]

# Using pip
pip install feishu-webhook-bot[webui]
```

Includes:

- `nicegui` - Web UI framework

### MCP (Model Context Protocol)

```bash
# Using uv
uv add feishu-webhook-bot[mcp]

# Using pip
pip install feishu-webhook-bot[mcp]
```

Includes:

- `mcp` - MCP client library

### All Optional Dependencies

```bash
# Using uv
uv add feishu-webhook-bot[all]

# Using pip
pip install feishu-webhook-bot[all]
```

### Manual Installation of Optional Dependencies

```bash
# AI providers
pip install openai anthropic google-generativeai

# Web UI
pip install nicegui

# MCP
pip install mcp

# Database (for auth/persistence)
pip install aiosqlite

# HTTP client enhancements
pip install httpx[http2]
```

## Development Installation

For contributing or development:

```bash
# Clone the repository
git clone https://github.com/AstroAir/feishu-webhook-bot.git
cd feishu-webhook-bot

# Install with all development dependencies
uv sync --all-groups

# Or using pip
pip install -e ".[dev,test,docs]"
```

### Development Dependencies

| Group | Packages | Purpose |
|-------|----------|---------|
| `dev` | ruff, black, mypy | Code quality |
| `test` | pytest, pytest-cov, pytest-asyncio | Testing |
| `docs` | mkdocs, mkdocs-material, mkdocstrings | Documentation |

### Setting Up Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Verification

### Verify Installation

```bash
# Check version
feishu-webhook-bot --version

# Or via Python
python -c "import feishu_webhook_bot; print(feishu_webhook_bot.__version__)"
```

### Test Basic Functionality

```bash
# Generate default config
feishu-webhook-bot init -o config.yaml

# Check config is valid
python -c "from feishu_webhook_bot.core import BotConfig; BotConfig.from_yaml('config.yaml')"
```

### Send Test Message

```bash
# Send a test message (replace with your webhook URL)
feishu-webhook-bot send -w "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_URL" -t "Hello!"
```

## Upgrading

### Using uv

```bash
# Upgrade to latest version
uv add feishu-webhook-bot --upgrade

# Upgrade to specific version
uv add feishu-webhook-bot==1.2.0
```

### Using pip

```bash
# Upgrade to latest version
pip install --upgrade feishu-webhook-bot

# Upgrade to specific version
pip install feishu-webhook-bot==1.2.0
```

### From Source

```bash
cd feishu-webhook-bot
git pull origin main
uv sync
```

### Migration Notes

When upgrading between major versions, check the [Changelog](../resources/changelog.md) for breaking changes and migration guides.

## Uninstallation

### Using uv

```bash
uv remove feishu-webhook-bot
```

### Using pip

```bash
pip uninstall feishu-webhook-bot
```

### Using pipx

```bash
pipx uninstall feishu-webhook-bot
```

### Clean Up

```bash
# Remove configuration files
rm -rf config.yaml plugins/ data/ logs/

# Remove cache
rm -rf ~/.cache/feishu-webhook-bot
```

## Troubleshooting Installation

### Python Version Issues

```text
ERROR: Package requires Python >=3.10
```

**Solution**: Upgrade Python or use pyenv:

```bash
# Using pyenv
pyenv install 3.12
pyenv local 3.12
```

### Permission Errors

```text
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Solution**: Use virtual environment or `--user` flag:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Then install
pip install feishu-webhook-bot
```

### Network Issues

```text
ERROR: Could not find a version that satisfies the requirement
```

**Solution**: Check network connection or use mirror:

```bash
# Use PyPI mirror
pip install feishu-webhook-bot -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Missing System Dependencies

Some features may require system-level dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev libffi-dev

# CentOS/RHEL
sudo yum install python3-devel libffi-devel

# macOS
brew install libffi
```

## Next Steps

After installation:

1. [Quick Start](quickstart.md) - Get up and running in 5 minutes
2. [Configuration Reference](../guides/configuration-reference.md) - Configure your bot
3. [First Steps](first-steps.md) - Detailed setup guide

## See Also

- [Deployment Guide](../deployment/deployment.md) - Production deployment
- [Troubleshooting](../resources/troubleshooting.md) - Common issues
- [FAQ](../resources/faq.md) - Frequently asked questions
