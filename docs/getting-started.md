# Getting Started with Feishu Webhook Bot

This guide will help you get started with the Feishu Webhook Bot framework.

## Prerequisites

- Python 3.12 or higher
- A Feishu (Lark) account
- Access to create webhooks in Feishu

## Installation

### Step 1: Install uv (Recommended)

uv is a fast Python package installer and resolver.

**Windows (PowerShell):**

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**macOS/Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/AstroAir/feishu-webhook-bot.git
cd feishu-webhook-bot
```

### Step 3: Install Dependencies

```bash
uv sync --all-groups
```

This will create a virtual environment and install all dependencies.

## Setting Up Your Feishu Webhook

### 1. Create a Feishu Group

1. Open Feishu app
2. Click "+" to create a new group
3. Add members as needed

### 2. Add Custom Bot

1. In the group, click the group settings icon
2. Navigate to "Bots" or "Group Bots"
3. Click "Add Bot"
4. Choose "Custom Bot"
5. Give your bot a name and avatar
6. Copy the webhook URL provided

### 3. (Optional) Enable Webhook Signing

For enhanced security, you can enable webhook signing:

1. When creating the bot, look for "Security Settings"
2. Enable "Signature Verification"
3. Copy the signing secret
4. Use this secret in your configuration

## Configuration

### Generate Default Configuration

```bash
feishu-webhook-bot init --output config.yaml
```

This creates a `config.yaml` file with default settings.

### Edit Configuration

Open `config.yaml` and update the webhook URL:

```yaml
webhooks:
  - name: "default"
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL"
    secret: "your-secret-if-enabled"  # Optional

scheduler:
  enabled: true
  timezone: "Asia/Shanghai"  # Your timezone

plugins:
  enabled: true
  plugin_dir: "plugins"
  auto_reload: true

logging:
  level: "INFO"
  log_file: "logs/bot.log"

http:
  timeout: 10.0
  retry:
    max_attempts: 3
    backoff_seconds: 1.0
    backoff_multiplier: 2.0
    max_backoff_seconds: 30.0

templates: []
automations: []
event_server:
  enabled: false
  host: "0.0.0.0"
  port: 8000
  path: "/feishu/events"
```

All configuration values support environment-variable expansion. For example, you
can keep secrets out of version control by setting:

```powershell
$env:FEISHU_WEBHOOK_SECRET = "super-secret"
```

and referencing `${FEISHU_WEBHOOK_SECRET}` in `config.yaml`.

### Declarative Automations

You can define scheduled or event-driven workflows without writing Python code.

```yaml
automations:
  - name: "daily-summary"
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments: { day_of_week: "mon-fri", hour: "9", minute: "30" }
    actions:
      - type: "send_text"
        text: "Good morning! Here is your daily summary."
```

Automation actions support `send_text`, `send_template`, and `http_request`. Use
`http_request` to call external APIs and stash the JSON response for the next
action in the chain.

### Message Templates

Define templates once and reuse them in automations or plugins:

```yaml
templates:
  - name: "simple-card"
    type: "card"
    content: |
      { "header": { "title": { "tag": "plain_text", "content": "${title}" } },
        "elements": [ { "tag": "markdown", "content": "${body}" } ] }
```

Render the template from an automation:

```yaml
actions:
  - type: "send_template"
    template: "simple-card"
    context:
      title: "Morning Update"
      body: "All systems operational."
```

### Webhook Event Server

Set `event_server.enabled: true` to spin up a FastAPI listener that accepts
Feishu events and routes them to automations and plugins:

```yaml
event_server:
  enabled: true
  verification_token: "${FEISHU_EVENT_TOKEN}"
  signature_secret: "${FEISHU_EVENT_SECRET}"
```

Point your Feishu app's event webhook to `http://host:port/path`. Use the
`Plugin.handle_event` hook or automation event triggers to react without
polling.

### Create Plugin Directory

```bash
mkdir plugins
```

## Running the Bot

### Start the Bot

```bash
feishu-webhook-bot start --config config.yaml
```

You should see output like:

```text
2024-01-01 10:00:00 - setup - INFO - Logging configured: level=INFO
2024-01-01 10:00:00 - bot - INFO - Feishu Bot initialized
2024-01-01 10:00:00 - client - INFO - Webhook client initialized: default
2024-01-01 10:00:00 - scheduler - INFO - Scheduler initialized
2024-01-01 10:00:00 - bot - INFO - 🚀 Feishu Bot is running!
```

The bot will send a startup message to your Feishu group!

### Stop the Bot

Press `Ctrl+C` to stop the bot gracefully.

## Testing Your Setup

### Send a Test Message

```bash
feishu-webhook-bot send \
  --webhook "YOUR_WEBHOOK_URL" \
  --text "Hello from Feishu Bot!"
```

If configured correctly, you should receive the message in your Feishu group.

## Creating Your First Plugin

### 1. Create Plugin File

Create `plugins/hello_world.py`:

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class HelloWorldPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="hello-world",
            version="1.0.0",
            description="A simple hello world plugin"
        )
    
    def on_enable(self) -> None:
        # Send message every minute
        self.register_job(
            self.send_hello,
            trigger='interval',
            minutes=1
        )
    
    def send_hello(self) -> None:
        self.client.send_text("👋 Hello from Hello World plugin!")
```

### 2. Restart the Bot

If hot-reload is disabled, restart the bot:

```bash
feishu-webhook-bot start --config config.yaml
```

With hot-reload enabled, the plugin will be loaded automatically when you save the file!

### 3. Check Logs

You should see:

```text
INFO - Plugin loaded: hello-world
INFO - Plugin enabled: hello-world
INFO - Scheduled jobs: hello_world.send_hello
```

## Using Example Plugins

The framework includes several example plugins in the `plugins/` directory:

### Daily Greeting Plugin

Sends good morning messages at 9 AM - already in `plugins/daily_greeting.py`

### System Monitor Plugin

Monitors system resources and sends reports - located at `plugins/system_monitor.py`

### Reminder Plugin

Sends customizable reminders throughout the day - located at `plugins/reminder.py`

## Next Steps

### Customize Your Setup

1. **Add more webhooks**: Configure multiple webhooks for different purposes
2. **Adjust timezone**: Change the scheduler timezone in config.yaml
3. **Configure logging**: Adjust log level and file location

### Develop Custom Plugins

1. Read the [Plugin Development Guide](plugin-guide.md)
2. Study the example plugins
3. Create your own plugins for custom workflows

### Advanced Features

1. **Persistent job storage**: Switch to SQLite job store for persistence
2. **Environment variables**: Use environment variables for sensitive config
3. **Declarative automations**: Link multiple actions (API calls + messages) using the new `automations` section
4. **Multiple bots**: Run multiple bot instances with different configs

## Troubleshooting

### Bot Not Starting

**Problem:** Bot fails to start with "Webhook URL cannot be empty"

**Solution:** Make sure you've updated the webhook URL in config.yaml

### Plugin Not Loading

**Problem:** Plugin file exists but doesn't load

**Solution:**

- Check that filename doesn't start with underscore
- Verify class inherits from `BasePlugin`
- Check logs for error messages

### Messages Not Sending

**Problem:** No messages appear in Feishu group

**Solution:**

- Verify webhook URL is correct
- Check if bot is still in the group
- Look for error messages in logs
- Test with `feishu-webhook-bot send` command

### Hot-Reload Not Working

**Problem:** Plugin changes don't take effect

**Solution:**

- Ensure `auto_reload: true` in config.yaml
- Check that `plugin_dir` path is correct
- Verify watchdog is installed: `uv pip list | grep watchdog`

## Getting Help

- 📖 Read the [full documentation](../README.md)
- 🐛 Report issues on [GitHub](https://github.com/AstroAir/feishu-webhook-bot/issues)
- 💬 Ask questions in [Discussions](https://github.com/AstroAir/feishu-webhook-bot/discussions)

## What's Next?

- Explore the [Plugin Development Guide](plugin-guide.md)
- Review the [API Documentation](api.md)
- Check out [Contributing Guidelines](../CONTRIBUTING.md)

Happy bot building! 🚀
