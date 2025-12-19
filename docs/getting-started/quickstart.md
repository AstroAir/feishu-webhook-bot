# Quick Start

Get your Feishu bot up and running in 5 minutes.

## Prerequisites

- Python 3.10+
- A Feishu webhook URL ([How to get one](#getting-a-webhook-url))

## Step 1: Install

```bash
# Using uv (recommended)
uv add feishu-webhook-bot

# Or using pip
pip install feishu-webhook-bot
```

## Step 2: Create Configuration

```bash
feishu-webhook-bot init -o config.yaml
```

Edit `config.yaml` and add your webhook URL:

```yaml
webhooks:
  - name: default
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL"
    # secret: "your-signing-secret"  # Optional
```

## Step 3: Send Your First Message

```bash
feishu-webhook-bot send -w "YOUR_WEBHOOK_URL" -t "Hello from my bot!"
```

## Step 4: Create a Simple Bot

Create `main.py`:

```python
from feishu_webhook_bot import FeishuBot

# Create and start bot
bot = FeishuBot.from_config("config.yaml")

# Send a message
bot.send_text("🚀 Bot is online!")

# Start the bot (with scheduler and plugins)
bot.start()
```

Run it:

```bash
python main.py
```

## Step 5: Add a Plugin

Create `plugins/hello.py`:

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class HelloPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="hello",
            version="1.0.0",
            description="A simple hello plugin",
        )

    def on_enable(self) -> None:
        # Send message when plugin loads
        self.client.send_text("👋 Hello plugin enabled!")

        # Schedule a daily greeting
        self.register_job(
            self.daily_greeting,
            trigger='cron',
            hour=9,
            minute=0,
        )

    def daily_greeting(self) -> None:
        self.client.send_text("☀️ Good morning!")
```

Restart your bot to load the plugin.

## Step 6: Add Automation

Add to `config.yaml`:

```yaml
automation:
  rules:
    - name: "hourly-status"
      trigger:
        type: schedule
        cron: "0 * * * *"  # Every hour
      action:
        type: send_text
        text: "📊 System status: OK"
        webhooks: ["default"]
```

## What's Next?

### Send Different Message Types

```python
# Text message
bot.send_text("Hello!")

# Markdown
bot.send_markdown("**Bold** and *italic*")

# Interactive card
from feishu_webhook_bot.core.client import CardBuilder

card = (
    CardBuilder()
    .set_header("Notification", template="blue")
    .add_markdown("Important message here")
    .add_button("View", url="https://example.com")
    .build()
)
bot.send_card(card)
```

### Use Templates

```yaml
# config.yaml
templates:
  alert:
    type: card
    header:
      title: "⚠️ Alert: {title}"
      template: red
    elements:
      - type: markdown
        content: "{message}"
```

```python
bot.send_template("alert", title="High CPU", message="CPU usage is 95%")
```

### Enable AI Features

```yaml
# config.yaml
ai:
  enabled: true
  model: "openai:gpt-4o"
  api_key: "${OPENAI_API_KEY}"
```

```python
response = bot.ai_agent.chat("user123", "What's the weather like?")
print(response)
```

### Use Chat Controller for Multi-Platform

```python
from feishu_webhook_bot.chat import create_chat_controller, ChatConfig

# Create chat controller with AI and command support
controller = create_chat_controller(
    ai_agent=bot.ai_agent,
    providers=bot.providers,
    config=ChatConfig(
        require_at_in_groups=True,
        enable_commands=True,
    ),
)

# Handle incoming messages
await controller.handle_incoming(message)
```

## Getting a Webhook URL

1. Open [Feishu Open Platform](https://open.feishu.cn/)
2. Create a new custom bot
3. Go to **Bot** → **Webhook**
4. Copy the webhook URL
5. (Optional) Set a signing secret for security

## Common Commands

```bash
# Start bot
feishu-webhook-bot start

# Start with debug logging
feishu-webhook-bot start --debug

# Start web UI
feishu-webhook-bot webui

# List plugins
feishu-webhook-bot plugins

# Send test message
feishu-webhook-bot send -w "URL" -t "Test"
```

## Project Structure

A typical project looks like:

```text
my-bot/
├── config.yaml          # Bot configuration
├── main.py              # Entry point
├── plugins/             # Custom plugins
│   ├── __init__.py
│   └── my_plugin.py
├── templates/           # Message templates
└── data/                # Runtime data
```

## Troubleshooting

### Bot not sending messages

1. Check webhook URL is correct
2. Verify bot is in the chat/group
3. Check network connectivity

### Plugins not loading

1. Ensure plugins are in `plugins/` directory
2. Check for Python syntax errors
3. Verify plugin inherits from `BasePlugin`

### Configuration errors

```bash
# Validate configuration
python -c "from feishu_webhook_bot.core import BotConfig; BotConfig.from_yaml('config.yaml')"
```

## Learn More

- [Installation Guide](installation.md) - Detailed installation options
- [First Steps](first-steps.md) - Complete setup guide
- [Plugin Development](../guides/plugin-guide.md) - Create custom plugins
- [Configuration Reference](../guides/configuration-reference.md) - All configuration options
- [Examples](../resources/examples.md) - More code examples
