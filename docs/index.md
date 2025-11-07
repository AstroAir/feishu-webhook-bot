# Welcome to Feishu Webhook Bot

A production-ready framework for building powerful Feishu (Lark) webhook bots with messaging, scheduling, plugins, and automation capabilities.

## 🚀 Quick Links

- **[Getting Started](getting-started.md)** - Installation, setup, and first bot
- **[Plugin Development Guide](plugin-guide.md)** - Create custom plugins with scheduling
- **[Automation Guide](automation-guide.md)** - Declarative workflows and event handling
- **[API Reference](api.md)** - Complete API documentation
- **[Contributing](contributing.md)** - Development guidelines

## ✨ Key Features

- **📨 Rich Messaging** - Text, rich text, interactive cards (JSON v2.0), and images
- **⏰ Task Scheduling** - Built-in APScheduler for cron jobs and periodic tasks
- **🔌 Plugin System** - Extensible architecture with hot-reload support
- **🤖 Automation Engine** - Declarative workflows triggered by schedules or events
- **⚙️ Configuration** - YAML/JSON config with Pydantic validation
- **📝 Logging** - Comprehensive logging with rotation and Rich formatting
- **🔄 Hot Reload** - Automatically reload plugins and configurations without restart
- **🛡️ Security** - HMAC-SHA256 signing support for secure webhooks
- **🌐 Event Server** - FastAPI server for receiving Feishu webhook events
- **🎨 Web UI** - NiceGUI-based configuration and control panel

## 📚 Documentation Structure

### For Users

1. **Getting Started** - Set up your first bot in minutes
2. **Plugin Development** - Build custom plugins for your use cases
3. **Automation Guide** - Create declarative workflows
4. **Configuration Reference** - All available configuration options

### For Developers

1. **API Reference** - Complete API documentation
2. **Contributing** - How to contribute to the project
3. **Architecture** - Understanding the codebase structure

## 🎯 Common Tasks

### Send a Message

```python
from feishu_webhook_bot.core import FeishuWebhookClient, WebhookConfig

config = WebhookConfig(url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx")
client = FeishuWebhookClient(config)
client.send_text("Hello, Feishu!")
```

### Create a Plugin

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="my-plugin", version="1.0.0")

    def on_enable(self) -> None:
        self.register_job(self.my_task, trigger='interval', minutes=5)

    def my_task(self) -> None:
        self.client.send_text("Task executed!")
```

### Define an Automation

```yaml
automations:
  - name: "daily-report"
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments: { hour: "9", minute: "0" }
    actions:
      - type: "send_text"
        text: "Good morning!"
```

## 🔗 External Resources

- [Feishu Open Platform](https://open.feishu.cn/)
- [Feishu Cards Documentation](https://open.feishu.cn/document/feishu-cards/feishu-card-overview)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## 💬 Getting Help

- 📖 Read the full [documentation](.)
- 🐛 Report issues on [GitHub](https://github.com/AstroAir/feishu-webhook-bot/issues)
- 💬 Ask questions in [Discussions](https://github.com/AstroAir/feishu-webhook-bot/discussions)

---

**Ready to get started?** Head over to [Getting Started](getting-started.md)!
