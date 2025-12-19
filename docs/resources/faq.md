# Frequently Asked Questions

Common questions and answers about the Feishu Webhook Bot framework.

## Table of Contents

- [General](#general)
- [Installation](#installation)
- [Configuration](#configuration)
- [Messaging](#messaging)
- [Plugins](#plugins)
- [Scheduling](#scheduling)
- [AI Features](#ai-features)
- [Security](#security)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)

## General

### What is Feishu Webhook Bot?

Feishu Webhook Bot is a Python framework for building powerful, plugin-driven bots for Feishu (Lark). It provides:

- Easy message sending via webhooks
- Plugin system with hot-reload
- Task scheduling with APScheduler
- Declarative automation rules
- AI integration with multiple providers
- Multi-platform support (Feishu, QQ)

### What Python versions are supported?

Python 3.10 and above are supported. We recommend Python 3.12 for best performance.

### Is it production-ready?

Yes! The framework includes:

- Circuit breaker for fault tolerance
- Message queue for reliable delivery
- Comprehensive logging
- Authentication system
- Deployment guides for Docker, Kubernetes, and systemd

### Can I use it with Lark (international version)?

Yes, the framework works with both Feishu (China) and Lark (international). Just use the appropriate webhook URL.

### Is it open source?

Yes, the project is open source under the MIT license. Contributions are welcome!

## Installation

### How do I install the framework?

```bash
# Using uv (recommended)
uv add feishu-webhook-bot

# Using pip
pip install feishu-webhook-bot
```

See [Installation Guide](../getting-started/installation.md) for more options.

### What are the optional dependencies?

| Extra | Packages | Purpose |
|-------|----------|---------|
| `ai` | openai, anthropic | AI features |
| `webui` | nicegui | Web interface |
| `mcp` | mcp | MCP integration |
| `all` | All above | Everything |

Install with: `pip install feishu-webhook-bot[ai]`

### How do I update to the latest version?

```bash
# Using uv
uv add feishu-webhook-bot --upgrade

# Using pip
pip install --upgrade feishu-webhook-bot
```

## Configuration

### Where should I put my configuration file?

The default location is `config.yaml` in your project root. You can specify a different path:

```bash
feishu-webhook-bot start -c /path/to/config.yaml
```

### How do I use environment variables in config?

Use `${VAR_NAME}` syntax:

```yaml
webhooks:
  - name: default
    url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_SECRET}"
```

### Can I use JSON instead of YAML?

Yes, use `.json` extension:

```python
config = BotConfig.from_json("config.json")
```

### How do I validate my configuration?

```bash
python -c "from feishu_webhook_bot.core import BotConfig; BotConfig.from_yaml('config.yaml')"
```

### Does configuration support hot-reload?

Yes, enable the config watcher:

```yaml
general:
  hot_reload: true
```

## Messaging

### How do I send a simple text message?

```python
from feishu_webhook_bot import FeishuBot

bot = FeishuBot.from_config("config.yaml")
bot.send_text("Hello, World!")
```

### How do I send a message to a specific webhook?

```python
bot.send_text("Hello!", webhook="alerts")
```

### What message types are supported?

- Text messages
- Markdown messages
- Rich text (post format)
- Interactive cards
- Images

### How do I send an interactive card?

```python
from feishu_webhook_bot.core.client import CardBuilder

card = (
    CardBuilder()
    .set_header("Title", template="blue")
    .add_markdown("Content here")
    .add_button("Click me", url="https://example.com")
    .build()
)
bot.send_card(card)
```

### Is there a message size limit?

Yes, Feishu has limits:

- Text: ~4000 characters
- Card: ~30KB JSON

Split large messages or use multiple cards.

### How do I handle message failures?

Enable retry and circuit breaker:

```yaml
webhooks:
  - name: default
    retry:
      max_retries: 3
      retry_delay: 1.0

circuit_breaker:
  enabled: true
  failure_threshold: 5
```

## Plugins

### How do I create a plugin?

Create a file in `plugins/` directory:

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="my-plugin", version="1.0.0")

    def on_enable(self) -> None:
        self.client.send_text("Plugin enabled!")
```

### How do I configure a plugin?

Add settings in config.yaml:

```yaml
plugins:
  plugin_settings:
    my-plugin:
      setting1: "value1"
      setting2: 42
```

Access in plugin:

```python
value = self.get_config("setting1", "default")
```

### How does hot-reload work?

When enabled, plugins are automatically reloaded when their files change:

```yaml
plugins:
  auto_reload: true
  reload_interval: 5.0
```

### Can plugins communicate with each other?

Yes, use the event system:

```python
# Emit event
self.emit_event("my_event", {"data": "value"})

# Subscribe to event
self.subscribe_event("my_event", self.handler)
```

### How do I disable a plugin?

```yaml
plugins:
  disabled_plugins:
    - "plugin-name"
```

## Scheduling

### How do I schedule a task?

In a plugin:

```python
self.register_job(
    self.my_task,
    trigger='cron',
    hour=9,
    minute=0,
)
```

Or in config:

```yaml
automation:
  rules:
    - name: "my-task"
      trigger:
        type: schedule
        cron: "0 9 * * *"
      action:
        type: send_text
        text: "Scheduled message"
```

### What scheduling options are available?

- **Interval**: Run every N seconds/minutes/hours
- **Cron**: Run on cron schedule
- **Date**: Run once at specific time

### How do I persist jobs across restarts?

Use SQLite job store:

```yaml
scheduler:
  job_store_type: "sqlite"
  job_store_path: "data/jobs.db"
```

### What timezone does the scheduler use?

Configure in config:

```yaml
scheduler:
  timezone: "Asia/Shanghai"
```

## AI Features

### What AI providers are supported?

- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Azure OpenAI
- Local models via OpenAI-compatible API

### How do I enable AI features?

```yaml
ai:
  enabled: true
  model: "openai:gpt-4o"
  api_key: "${OPENAI_API_KEY}"
```

### How do I use AI in my code?

```python
response = bot.ai_agent.chat("user123", "Hello!")
print(response)
```

### Does AI support conversation history?

Yes, conversations are tracked per user:

```yaml
ai:
  conversation:
    max_history: 20
    ttl: 3600  # 1 hour
```

### What is MCP integration?

MCP (Model Context Protocol) allows AI to use external tools:

```yaml
ai:
  mcp:
    enabled: true
    servers:
      - name: "filesystem"
        command: "npx"
        args: ["-y", "@anthropic/mcp-server-filesystem", "/path"]
```

### How do I use the Chat Controller?

The ChatController provides unified multi-platform chat handling:

```python
from feishu_webhook_bot.chat import create_chat_controller, ChatConfig

controller = create_chat_controller(
    ai_agent=bot.ai_agent,
    providers=bot.providers,
    config=ChatConfig(require_at_in_groups=True),
)

await controller.handle_incoming(message)
```

### What commands are available?

Built-in commands include:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/reset` | Clear conversation history |
| `/model` | Switch AI model |
| `/status` | Show bot status |
| `/clear` | Clear current context |

### How do I add custom commands?

```python
@controller.command_handler.register("/mycommand")
async def my_command(handler, message, args):
    return CommandResult(True, "Command executed!")
```

### Can I store conversation history?

Yes, use the PersistentConversationManager:

```python
from feishu_webhook_bot.ai.conversation_store import PersistentConversationManager

manager = PersistentConversationManager("sqlite:///conversations.db")
```

## Security

### How do I secure my webhook?

Use signing secret:

```yaml
webhooks:
  - name: default
    url: "https://..."
    secret: "${FEISHU_SECRET}"
```

### How do I enable authentication?

```yaml
auth:
  enabled: true
  jwt_secret: "${JWT_SECRET}"
```

### Should I store secrets in config?

No, use environment variables:

```yaml
api_key: "${API_KEY}"  # Good
api_key: "sk-xxx"      # Bad
```

### How do I protect the Web UI?

Enable authentication:

```yaml
auth:
  enabled: true
```

## Performance

### How many messages can it handle?

Depends on your setup. With message queue:

- Single instance: ~100 msg/sec
- With queue: ~1000 msg/sec

### How do I improve performance?

1. Enable message queue
2. Use circuit breaker
3. Enable HTTP/2
4. Use connection pooling

```yaml
message_queue:
  enabled: true
  batch_size: 10

http_client:
  http2: true
  max_connections: 100
```

### Does it support horizontal scaling?

Yes, but requires:

- External job store (Redis/PostgreSQL)
- External message queue
- Leader election for singleton tasks

## Troubleshooting

### Bot not sending messages

1. Check webhook URL is correct
2. Verify bot is in the group
3. Check network connectivity
4. Enable debug logging

### Plugins not loading

1. Check file is in `plugins/` directory
2. Verify syntax: `python -m py_compile plugins/my_plugin.py`
3. Ensure it inherits from `BasePlugin`

### Configuration errors

```bash
# Validate config
python -c "from feishu_webhook_bot.core import BotConfig; BotConfig.from_yaml('config.yaml')"
```

### Where can I get help?

- [Troubleshooting Guide](troubleshooting.md)
- [GitHub Issues](https://github.com/AstroAir/feishu-webhook-bot/issues)
- [GitHub Discussions](https://github.com/AstroAir/feishu-webhook-bot/discussions)

## See Also

- [Quick Start](../getting-started/quickstart.md) - Get started quickly
- [Configuration Reference](../guides/configuration-reference.md) - All options
- [Troubleshooting](troubleshooting.md) - Common issues
- [Examples](examples.md) - Code examples
