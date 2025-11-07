# Feishu Webhook Bot Framework

> 🚀 A production-ready framework for building Feishu (Lark) webhook bots with messaging, scheduling, plugins, and hot-reload capabilities.

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ Features

- **📨 Rich Messaging**: Support for text, rich text, interactive cards (JSON v2.0), and images
- **⏰ Task Scheduling**: Built-in APScheduler for cron jobs and periodic tasks
- **🔌 Plugin System**: Extensible architecture with hot-reload support
- **🔐 Authentication**: Complete user authentication system with JWT tokens and secure password hashing
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

#### Text Messages

```python
from feishu_webhook_bot.core import FeishuWebhookClient, WebhookConfig

config = WebhookConfig(url="https://...", secret="...")
client = FeishuWebhookClient(config)

# Send plain text
client.send_text("Hello, Feishu!")
```

#### Rich Text Messages

```python
# Send rich text with formatting and links
content = [
    [
        {"tag": "text", "text": "Hello "},
        {"tag": "a", "text": "click here", "href": "https://example.com"}
    ]
]
client.send_rich_text("Title", content)
```

#### Interactive Cards with CardBuilder

```python
from feishu_webhook_bot.core.client import CardBuilder

# Build an interactive card
card = (
    CardBuilder()
    .set_config(wide_screen_mode=True)
    .set_header("Notification", template="blue")
    .add_markdown("**Important:** This is a test message")
    .add_divider()
    .add_text("Additional information")
    .add_button("View Details", url="https://example.com")
    .add_note("Footer note")
    .build()
)
client.send_card(card)
```

#### Image Messages

```python
# Send an image
client.send_image(
    image_key="img_xxx",  # Image key from Feishu
    title="Image Title"
)
```

### CardBuilder Methods

The `CardBuilder` class provides a fluent API for building interactive cards:

- `set_config(**kwargs)` - Set card configuration (e.g., `wide_screen_mode=True`)
- `set_header(title, template="blue")` - Set card header with template color
- `add_markdown(content)` - Add markdown element
- `add_text(content)` - Add plain text element
- `add_divider()` - Add visual divider
- `add_button(text, url)` - Add clickable button
- `add_note(content)` - Add footer note
- `build()` - Build and return the card JSON

Available header templates: `blue`, `red`, `orange`, `yellow`, `green`, `turquoise`, `purple`

## 🤖 Automation & Workflows

The framework supports declarative automation workflows that can be triggered by schedules or events:

```yaml
automations:
  - name: "daily-summary"
    description: "Send a summary every weekday at 9:30"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          day_of_week: "mon-fri"
          hour: "9"
          minute: "30"
    default_webhooks: ["default"]
    actions:
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/summary"
          save_as: "summary"
      - type: "send_template"
        template: "daily_summary"
        context:
          date: "${event_date}"
          data: "${summary.data}"
        webhooks: ["default"]
```

### Message Templates

Define reusable templates with variable substitution:

```yaml
templates:
  - name: "daily_summary"
    description: "Daily summary card"
    type: "card"
    engine: "string"  # or "format"
    content: |
      {
        "header": {
          "template": "blue",
          "title": {"tag": "plain_text", "content": "Daily Summary"}
        },
        "elements": [
          {
            "tag": "markdown",
            "content": "**Date:** ${date}\n**Status:** ${status}"
          }
        ]
      }
```

### Event Server

Enable the event server to receive Feishu webhook events:

```yaml
event_server:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  path: "/feishu/events"
  verification_token: "${FEISHU_EVENT_TOKEN}"
  signature_secret: "${FEISHU_EVENT_SECRET}"
```

Then configure automations to react to events:

```yaml
automations:
  - name: "react-to-message"
    trigger:
      type: "event"
      event:
        event_type: "im.message.receive_v1"
        conditions:
          - path: "event.message.content"
            operator: "contains"
            value: "alert"
    actions:
      - type: "send_text"
        text: "Alert received!"
        webhooks: ["default"]
```

## 🔐 Authentication System

The framework includes a complete authentication system with user registration, login, and session management.

### Quick Start

Enable authentication in your `config.yaml`:

```yaml
auth:
  enabled: true
  database_url: "sqlite:///./auth.db"
  jwt_secret_key: "your-super-secret-key-change-in-production"
  access_token_expire_minutes: 30
  max_failed_attempts: 5
  lockout_duration_minutes: 30
```

### Features

- **Secure Password Hashing**: Bcrypt with automatic salt generation
- **JWT Authentication**: Token-based authentication with configurable expiration
- **Password Strength Validation**: Enforces strong password requirements
- **Account Lockout**: Automatic lockout after failed login attempts
- **Rate Limiting**: Protection against brute force attacks
- **Email Validation**: Validates email format during registration
- **NiceGUI Integration**: Beautiful login and registration pages

### Usage Example

```python
from feishu_webhook_bot.auth.service import AuthService

auth_service = AuthService()

# Register a new user
user = auth_service.register_user(
    email="user@example.com",
    username="myusername",
    password="StrongPass123!",
    password_confirm="StrongPass123!"
)

# Authenticate user
user, token = auth_service.authenticate_user(
    login="user@example.com",
    password="StrongPass123!"
)
```

### Protecting Pages

```python
from nicegui import ui
from feishu_webhook_bot.auth.middleware import require_auth

@require_auth
@ui.page("/protected")
def protected_page():
    ui.label("This page requires authentication")
```

For complete documentation, see [Authentication Guide](docs/authentication.md).

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

### Environment Variables

All configuration values support environment variable expansion using `${VAR_NAME}` syntax:

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
export FEISHU_WEBHOOK_SECRET="your-secret"
```

Then in `config.yaml`:

```yaml
webhooks:
  - name: "default"
    url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_WEBHOOK_SECRET}"
```

### Webhooks

```yaml
webhooks:
  - name: "default"
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    secret: "your-signing-secret"  # Optional: for webhook signing
    timeout: 10.0  # Optional: request timeout in seconds
    headers:  # Optional: extra HTTP headers
      X-Custom-Header: "value"
    retry:  # Optional: retry policy
      max_attempts: 3
      backoff_seconds: 1.0
      backoff_multiplier: 2.0
      max_backoff_seconds: 30.0

  - name: "alerts"
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/yyy"
```

### Scheduler

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"  # Your timezone
  job_store_type: "memory"   # or "sqlite" for persistence
  job_store_path: "data/jobs.db"  # Required if using sqlite
```

### Plugins

```yaml
plugins:
  enabled: true
  plugin_dir: "plugins"  # Directory to scan for plugins
  auto_reload: true      # Enable hot-reload
  reload_delay: 1.0      # Delay before reloading (seconds)
```

### Logging

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  log_file: "logs/bot.log"  # null for console only
  max_bytes: 10485760  # Max log file size (10MB)
  backup_count: 5      # Number of backup files to keep
```

### HTTP Client

```yaml
http:
  timeout: 10.0  # Default request timeout
  retry:
    max_attempts: 3
    backoff_seconds: 1.0
    backoff_multiplier: 2.0
    max_backoff_seconds: 30.0
```

## 📚 Documentation

- [Feishu Cards Overview](https://open.feishu.cn/document/feishu-cards/feishu-card-overview)
- [Card JSON v2.0 Structure](https://open.feishu.cn/document/feishu-cards/card-json-v2-structure)
- [Webhook Documentation](https://www.feishu.cn/hc/zh-CN/articles/807992406756)

## 🏗️ Architecture

```text
feishu-webhook-bot/
├── src/feishu_webhook_bot/
│   ├── core/                  # Core functionality
│   │   ├── client.py          # Webhook client with CardBuilder
│   │   ├── config.py          # Configuration management (Pydantic)
│   │   ├── logger.py          # Logging utilities with Rich formatting
│   │   ├── event_server.py    # FastAPI event server for webhooks
│   │   └── templates.py       # Message template registry
│   ├── scheduler/             # Task scheduling
│   │   └── scheduler.py       # APScheduler wrapper with job decorator
│   ├── plugins/               # Plugin system
│   │   ├── base.py            # Base plugin class with lifecycle hooks
│   │   └── manager.py         # Plugin manager with hot-reload
│   ├── automation/            # Automation engine
│   │   └── engine.py          # Declarative workflow execution
│   ├── bot.py                 # Main bot orchestrator
│   ├── cli.py                 # Command-line interface
│   ├── config_ui.py           # NiceGUI web interface
│   └── __init__.py            # Public API exports
├── plugins/                   # User plugins directory
├── config.yaml                # Configuration file
├── config.example.yaml        # Example configuration
├── logs/                      # Log files
└── data/                      # Persistent data (jobs, state)
```

### Core Components

- **FeishuBot**: Main orchestrator that coordinates all components
- **FeishuWebhookClient**: Sends messages via Feishu webhooks with retry logic
- **TaskScheduler**: Manages scheduled jobs using APScheduler
- **PluginManager**: Discovers, loads, and manages plugins with hot-reload
- **AutomationEngine**: Executes declarative workflows based on schedules or events
- **EventServer**: FastAPI server for receiving Feishu webhook events
- **TemplateRegistry**: Manages reusable message templates

## 🧪 Development

### Testing

This project uses pytest for testing:

```bash
uv run pytest -q
```

### Code Quality

Format, lint, and type-check your code:

```bash
# Format code
uv run black .

# Lint code
uv run ruff check .

# Type-check
uv run mypy .

# All checks in one command
uv run ruff check . ; uv run black --check . ; uv run mypy . ; uv run pytest -q ; uv build
```

### Documentation

Build and serve the MkDocs documentation:

```bash
# Build docs
uv run mkdocs build --strict

# Serve locally
uv run mkdocs serve -a localhost:8000
```

### Task Runner

Cross-platform task runner scripts are available:

```bash
# Python task runner
uv run python scripts/tasks.py [task]

# Bash wrapper (Linux/macOS)
scripts/task.sh [task]

# PowerShell wrapper (Windows)
scripts/task.ps1 [task]
```

Available tasks: `setup`, `lint`, `format`, `typecheck`, `test`, `build`, `docs:build`, `docs:serve`, `ci`

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [httpx](https://www.python-httpx.org/), [APScheduler](https://apscheduler.readthedocs.io/), [Pydantic](https://docs.pydantic.dev/), and [NiceGUI](https://nicegui.io/)
- Inspired by the Feishu Open Platform documentation
- Thanks to all contributors!

## 📞 Support

- 📖 [Full Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/AstroAir/feishu-webhook-bot/issues)
- 💬 [Discussions](https://github.com/AstroAir/feishu-webhook-bot/discussions)

---

Made with ❤️ by the Feishu Bot Team
