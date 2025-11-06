# Feishu Webhook Bot Framework

> 🚀 A production-ready framework for building Feishu (Lark) webhook bots with messaging, scheduling, plugins, and hot-reload capabilities.

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ Features

- **📨 Rich Messaging**: Support for text, rich text, interactive cards (JSON v2.0), and images
- **⏰ Task Scheduling**: Built-in APScheduler for cron jobs and periodic tasks
- **🔌 Plugin System**: Extensible architecture with hot-reload support
- **⚙️ Configuration**: YAML/JSON config with Pydantic validation
- **📝 Logging**: Comprehensive logging with rotation and Rich formatting
- **🔄 Hot Reload**: Automatically reload plugins and configurations without restart
- **🛡️ Security**: HMAC-SHA256 signing support for secure webhooks

## Configuration Web UI (NiceGUI)

This project includes a local web interface to manage configuration, control the bot, and view logs.

Quick start:

- Install runtime dependencies (NiceGUI is required for the UI):

```powershell
pip install nicegui
```

- Launch the UI (default at <http://127.0.0.1:8080>):

```powershell
python -m feishu_webhook_bot.config_ui --config config.yaml --host 127.0.0.1 --port 8080
```

Or via the CLI shortcut:

```powershell
feishu-webhook-bot webui --config config.yaml --host 127.0.0.1 --port 8080
```

What you get:

- Edit all config sections (webhooks, scheduler, plugins, logging) with validation
- Start/Stop/Restart the bot and see current status
- View recent logs inline (set a log file in config to persist to disk)

## 📦 Installation

### Using uv (recommended)

First, install [uv](https://github.com/astral-sh/uv):

```powershell
# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

Then clone and install:

```bash
git clone https://github.com/AstroAir/feishu-webhook-bot.git
cd feishu-webhook-bot
uv sync --all-groups
```

### Using pip

```bash
pip install -e .
```

## 🚀 Quick Start

### 1. Initialize Configuration

Generate a default configuration file:

```bash
feishu-webhook-bot init --output config.yaml
```

### 2. Configure Webhook

Edit `config.yaml` and add your Feishu webhook URL:

```yaml
webhooks:
  - name: default
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL"
    secret: null  # Optional: add your webhook secret for security

scheduler:
  enabled: true
  timezone: "Asia/Shanghai"

plugins:
  enabled: true
  plugin_dir: "plugins"
  auto_reload: true

logging:
  level: "INFO"
  log_file: "logs/bot.log"
```

### 3. Create Plugin Directory

```bash
mkdir plugins
```

### 4. Start the Bot

```bash
feishu-webhook-bot start --config config.yaml
```

## 📖 Usage

### Command Line Interface

```bash
# Start bot with config
feishu-webhook-bot start --config config.yaml

# Generate default config
feishu-webhook-bot init --output config.yaml

# Send a test message
feishu-webhook-bot send --webhook "https://..." --text "Hello!"

# List loaded plugins
feishu-webhook-bot plugins --config config.yaml

# Show version
feishu-webhook-bot version
```

### Python API

```python
from feishu_webhook_bot import FeishuBot

# Start from config file
bot = FeishuBot.from_config("config.yaml")
bot.start()

# Or create programmatically
from feishu_webhook_bot.core import BotConfig, WebhookConfig

config = BotConfig(
    webhooks=[
        WebhookConfig(
            url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
            secret="your-secret"
        )
    ]
)
bot = FeishuBot(config)
bot.start()
```

### Sending Messages

```python
from feishu_webhook_bot.core import FeishuWebhookClient, WebhookConfig
from feishu_webhook_bot.core.client import CardBuilder

# Create client
config = WebhookConfig(url="https://...", secret="...")
client = FeishuWebhookClient(config)

# Send text message
client.send_text("Hello, Feishu!")

# Send rich text
content = [
    [
        {"tag": "text", "text": "Hello "},
        {"tag": "a", "text": "link", "href": "https://example.com"}
    ]
]
client.send_rich_text("Title", content)

# Send interactive card using CardBuilder
card = (
    CardBuilder()
    .set_header("Notification", template="blue")
    .add_markdown("**Important:** This is a test message")
    .add_divider()
    .add_button("View Details", url="https://example.com")
    .build()
)
client.send_card(card)
```

## 🔌 Plugin Development

### Creating a Plugin

Create a new file in the `plugins/` directory:

```python
# plugins/my_plugin.py
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from feishu_webhook_bot.core.client import CardBuilder

class MyPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="My custom plugin",
            author="Your Name"
        )
    
    def on_enable(self) -> None:
        # Schedule a task to run every 5 minutes
        self.register_job(
            self.my_task,
            trigger='interval',
            minutes=5
        )
        
        # Or use cron syntax (daily at 9 AM)
        self.register_job(
            self.daily_task,
            trigger='cron',
            hour='9',
            minute='0'
        )
    
    def my_task(self) -> None:
        """Task that runs every 5 minutes."""
        card = (
            CardBuilder()
            .set_header("Periodic Update", template="green")
            .add_markdown("Task executed successfully!")
            .build()
        )
        self.client.send_card(card)
    
    def daily_task(self) -> None:
        """Task that runs daily at 9 AM."""
        self.client.send_text("Good morning! Daily task executed.")
```

### Plugin Lifecycle

Plugins have several lifecycle hooks:

- `on_load()`: Called when plugin is loaded
- `on_enable()`: Called when bot starts and plugin is activated
- `on_disable()`: Called when bot stops or plugin is deactivated
- `on_unload()`: Called before hot-reload

### Example Plugins

The framework includes several example plugins:

- **daily_greeting.py**: Sends good morning messages at 9 AM
- **system_monitor.py**: Monitors CPU, memory, and disk usage
- **reminder.py**: Sends customizable reminders throughout the day
- **example_plugin.py**: Template for creating new plugins

## 📋 Configuration Reference

### Webhooks

```yaml
webhooks:
  - name: "default"
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    secret: "your-signing-secret"  # Optional
  - name: "alerts"
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/yyy"
```

### Scheduler

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  job_store_type: "memory"  # or "sqlite"
  job_store_path: "data/jobs.db"  # for sqlite
```

### Plugins

```yaml
plugins:
  enabled: true
  plugin_dir: "plugins"
  auto_reload: true
  reload_delay: 1.0  # seconds
```

### Logging

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  log_file: "logs/bot.log"
  max_bytes: 10485760  # 10MB
  backup_count: 5
```

## 📚 Documentation

- [Feishu Cards Overview](https://open.feishu.cn/document/feishu-cards/feishu-card-overview)
- [Card JSON v2.0 Structure](https://open.feishu.cn/document/feishu-cards/card-json-v2-structure)
- [Webhook Documentation](https://www.feishu.cn/hc/zh-CN/articles/807992406756)

## 🏗️ Architecture

```
feishu-webhook-bot/
├── src/feishu_webhook_bot/
│   ├── core/              # Core functionality
│   │   ├── client.py      # Webhook client
│   │   ├── config.py      # Configuration management
│   │   └── logger.py      # Logging utilities
│   ├── scheduler/         # Task scheduling
│   │   └── scheduler.py   # APScheduler wrapper
│   ├── plugins/           # Plugin system
│   │   ├── base.py        # Base plugin class
│   │   └── manager.py     # Plugin manager
│   ├── bot.py             # Main bot orchestrator
│   └── cli.py             # Command-line interface
├── plugins/               # User plugins directory
├── config.yaml            # Configuration file
└── logs/                  # Log files
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [httpx](https://www.python-httpx.org/), [APScheduler](https://apscheduler.readthedocs.io/), and [Pydantic](https://docs.pydantic.dev/)
- Inspired by the Feishu Open Platform documentation
- Thanks to all contributors!

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/AstroAir/feishu-webhook-bot/issues)
- 💬 [Discussions](https://github.com/AstroAir/feishu-webhook-bot/discussions)

---

Made with ❤️ by the Feishu Bot Team

- Format: `uv run black .`
- Lint: `uv run ruff check .`
- Type-check: `uv run mypy .`
- Tests: `uv run pytest -q`
- Build: `uv build`

Common one-liner to check everything:

```powershell
uv run ruff check . ; uv run black --check . ; uv run mypy . ; uv run pytest -q ; uv build
```

## Documentation (MkDocs)

This project includes a MkDocs site using the Material theme; docs live in `docs/`.

- Build docs: `uv run mkdocs build --strict`
- Serve docs locally: `uv run mkdocs serve -a localhost:8000`

The configuration lives in `mkdocs.yml`; content is in the `docs/` folder. API reference is generated from the package using `mkdocstrings`.

## Automation scripts

Cross-platform task runner scripts are provided in `scripts/`:

- Python task runner: `uv run python scripts/tasks.py [task]`
- Bash wrapper (Linux/macOS): `scripts/task.sh [task]`
- PowerShell wrapper (Windows): `scripts/task.ps1 [task]`

Available tasks: `setup`, `lint`, `format`, `typecheck`, `test`, `build`, `docs:build`, `docs:serve`, `ci` (all checks).

## Project Structure

```text
.
├─ src/
│  └─ python_quick_starter/
│     ├─ __init__.py
│     ├─ __main__.py
│     └─ cli.py
├─ tests/
│  └─ test_cli.py
├─ docs/
│  └─ index.md
├─ .github/workflows/ci.yml
├─ pyproject.toml
├─ README.md
├─ LICENSE
└─ CHANGELOG.md
```

## Testing

This project uses pytest. Configuration lives in `pyproject.toml` under `tool.pytest.ini_options`.

```powershell
uv run pytest -q
```

## Contributing

See `CONTRIBUTING.md` for guidelines. Issues and PRs are welcome.

## Releasing

A release workflow template is included at `.github/workflows/release.yml` and is commented out by default. To enable publishing to PyPI:

- Create a PyPI token and save it as `PYPI_API_TOKEN` in GitHub repo secrets
- Uncomment the publish step in `release.yml`
- Push a tag like `v0.1.0`

## License

MIT — see `LICENSE`.

````
