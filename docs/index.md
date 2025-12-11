# Welcome to Feishu Webhook Bot

A production-ready framework for building powerful Feishu (Lark) webhook bots with messaging, scheduling, plugins, AI capabilities, and automation.

## 🚀 Quick Links

### Getting Started

- **[Installation](getting-started/installation.md)** - Detailed installation guide
- **[Quick Start](getting-started/quickstart.md)** - Get running in 5 minutes
- **[First Steps](getting-started/first-steps.md)** - Complete setup guide

### User Guides

- **[Message Types](guides/message-types.md)** - All message formats
- **[Templates](guides/templates-guide.md)** - Message templates
- **[Event Handling](guides/event-handling.md)** - Handle Feishu events
- **[Chat Controller](guides/chat-controller-guide.md)** - Unified multi-platform chat handling
- **[Plugin Development](guides/plugin-guide.md)** - Create custom plugins
- **[Automation Guide](guides/automation-guide.md)** - Declarative workflows
- **[Task System](guides/tasks-guide.md)** - Advanced task execution
- **[Scheduler](guides/scheduler-guide.md)** - Job scheduling
- **[Multi-Provider](guides/providers-guide.md)** - Feishu, QQ/Napcat providers
- **[Web UI](guides/webui-guide.md)** - Configuration interface
- **[Configuration Reference](guides/configuration-reference.md)** - All configuration options

### AI Features

- **[AI Multi-Provider](ai/multi-provider.md)** - Multiple AI providers
- **[MCP Integration](ai/mcp-integration.md)** - Model Context Protocol
- **[AI Enhancements](ai/enhancements.md)** - Advanced AI features
- **[AI Tools](ai/tools.md)** - Tool calling and registry
- **[AI Commands](ai/commands.md)** - Chat command system (/help, /reset, etc.)
- **[Conversation Store](ai/conversation-store.md)** - Persistent conversation storage

### Security

- **[Authentication](security/authentication.md)** - User authentication
- **[Security Best Practices](security/security-best-practices.md)** - Security guide

### Deployment

- **[Deployment Guide](deployment/deployment.md)** - Production deployment
- **[Docker](deployment/docker.md)** - Docker deployment

### Reference

- **[API Reference](reference/api.md)** - Complete API documentation
- **[Core Components](reference/core-reference.md)** - Core architecture
- **[CLI Reference](reference/cli-reference.md)** - Command-line interface
- **[Error Codes](reference/error-codes.md)** - Error reference

### Resources

- **[Examples](resources/examples.md)** - Code examples
- **[FAQ](resources/faq.md)** - Frequently asked questions
- **[Troubleshooting](resources/troubleshooting.md)** - Common issues
- **[Migration Guide](resources/migration.md)** - Version migration
- **[Changelog](resources/changelog.md)** - Version history
- **[Contributing](resources/contributing.md)** - Development guidelines

## ✨ Key Features

- **📨 Rich Messaging** - Text, rich text, interactive cards (JSON v2.0), and images
- **🤖 AI Integration** - Built-in AI with pydantic-ai supporting multiple providers (OpenAI, Anthropic, Google, Groq, etc.)
- **🔗 MCP Support** - Model Context Protocol for standardized tool and resource access
- **🤝 Multi-Agent** - Agent orchestration (A2A) for complex multi-step tasks
- **⏰ Task Scheduling** - Built-in APScheduler for cron jobs and periodic tasks
- **📋 Task System** - Advanced task execution with dependencies, conditions, and templates
- **🔌 Plugin System** - Extensible architecture with hot-reload support
- **🤖 Automation Engine** - Declarative workflows triggered by schedules or events
- **🔐 Authentication** - Complete user authentication system with JWT tokens
- **⚙️ Configuration** - YAML/JSON config with Pydantic validation and hot-reload
- **📝 Logging** - Comprehensive logging with rotation and Rich formatting
- **🔄 Hot Reload** - Automatically reload plugins and configurations without restart
- **🛡️ Security** - HMAC-SHA256 signing, circuit breaker, and rate limiting
- **🌐 Event Server** - FastAPI server for receiving Feishu webhook events
- **🎨 Web UI** - NiceGUI-based configuration and control panel
- **📡 Multi-Provider** - Support for Feishu, QQ (Napcat), and custom providers
- **📊 Message Tracking** - Delivery tracking with persistence and deduplication
- **📬 Message Queue** - Async delivery with retry support

## 📚 Documentation Structure

### 📥 Getting Started

| Document                                        | Description                               |
| ----------------------------------------------- | ----------------------------------------- |
| [Installation](getting-started/installation.md) | System requirements, installation methods |
| [Quick Start](getting-started/quickstart.md)    | Get running in 5 minutes                  |
| [First Steps](getting-started/first-steps.md)   | Complete setup guide                      |

### 📖 User Guides

| Document                                           | Description                          |
| -------------------------------------------------- | ------------------------------------ |
| [Message Types](guides/message-types.md)           | Text, markdown, cards, images        |
| [Templates](guides/templates-guide.md)             | Reusable message templates           |
| [Event Handling](guides/event-handling.md)         | Handle Feishu events and callbacks   |
| [Chat Controller](guides/chat-controller-guide.md) | Unified multi-platform chat handling |
| [Plugin Development](guides/plugin-guide.md)       | Create custom plugins                |
| [Automation](guides/automation-guide.md)           | Declarative workflows                |
| [Task System](guides/tasks-guide.md)               | Advanced task execution              |
| [Scheduler](guides/scheduler-guide.md)             | Job scheduling                       |
| [Multi-Provider](guides/providers-guide.md)        | Feishu, QQ/Napcat providers          |
| [Web UI](guides/webui-guide.md)                    | Configuration interface              |

### ⚙️ Configuration

| Document                                                     | Description                    |
| ------------------------------------------------------------ | ------------------------------ |
| [Configuration Reference](guides/configuration-reference.md) | Complete configuration options |
| [YAML Configuration](guides/yaml-configuration-guide.md)     | YAML-specific features         |
| [Advanced YAML](guides/advanced-yaml-features.md)            | Advanced configuration         |

### 🤖 AI Features

| Document                                       | Description                     |
| ---------------------------------------------- | ------------------------------- |
| [AI Multi-Provider](ai/multi-provider.md)      | OpenAI, Anthropic, Google       |
| [MCP Integration](ai/mcp-integration.md)       | Model Context Protocol          |
| [AI Enhancements](ai/enhancements.md)          | Advanced AI features            |
| [AI Tools](ai/tools.md)                        | Tool calling and registry       |
| [AI Commands](ai/commands.md)                  | Chat command system             |
| [Conversation Store](ai/conversation-store.md) | Persistent conversation storage |

### 🔐 Security

| Document                                                       | Description                 |
| -------------------------------------------------------------- | --------------------------- |
| [Authentication](security/authentication.md)                   | User authentication and JWT |
| [Security Best Practices](security/security-best-practices.md) | Security hardening guide    |

### 🚀 Deployment

| Document                                     | Description               |
| -------------------------------------------- | ------------------------- |
| [Deployment Guide](deployment/deployment.md) | Production deployment     |
| [Docker](deployment/docker.md)               | Docker and Docker Compose |

### 📚 Reference

| Document                                       | Description                |
| ---------------------------------------------- | -------------------------- |
| [API Reference](reference/api.md)              | Complete API documentation |
| [Core Components](reference/core-reference.md) | Core architecture          |
| [CLI Reference](reference/cli-reference.md)    | Command-line interface     |
| [Error Codes](reference/error-codes.md)        | Error code reference       |

### 📦 Resources

| Document                                        | Description                |
| ----------------------------------------------- | -------------------------- |
| [Examples](resources/examples.md)               | Practical code examples    |
| [FAQ](resources/faq.md)                         | Frequently asked questions |
| [Troubleshooting](resources/troubleshooting.md) | Common issues              |
| [Migration Guide](resources/migration.md)       | Version migration          |
| [Changelog](resources/changelog.md)             | Version history            |
| [Contributing](resources/contributing.md)       | Development guidelines     |

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

## 🏗️ Architecture Overview

```text
feishu-webhook-bot/
├── src/feishu_webhook_bot/
│   ├── ai/                   # AI agents, MCP, multi-agent orchestration
│   │   ├── agent.py          # Main AIAgent class
│   │   ├── commands.py       # Chat command system (/help, /reset, etc.)
│   │   ├── config.py         # AI configuration models
│   │   ├── conversation.py   # Conversation management
│   │   ├── conversation_store.py # Persistent conversation storage
│   │   ├── exceptions.py     # AI-specific exceptions
│   │   ├── mcp_client.py     # MCP client implementation
│   │   ├── multi_agent.py    # Multi-agent orchestration
│   │   ├── retry.py          # Retry logic and circuit breaker
│   │   ├── task_integration.py # AI task integration
│   │   └── tools.py          # Tool registry and built-in tools
│   ├── auth/                 # Authentication system
│   │   ├── database.py       # Database operations
│   │   ├── middleware.py     # Auth middleware
│   │   ├── models.py         # User models
│   │   ├── routes.py         # FastAPI routes
│   │   ├── security.py       # Password hashing, JWT
│   │   ├── service.py        # Auth service
│   │   └── ui.py             # NiceGUI auth pages
│   ├── automation/           # Automation engine
│   │   └── engine.py         # AutomationEngine
│   ├── chat/                 # Unified chat controller
│   │   └── controller.py     # ChatController, ChatConfig, middleware
│   ├── core/                 # Core functionality
│   │   ├── circuit_breaker.py # Circuit breaker pattern
│   │   ├── client.py         # Webhook client, CardBuilder
│   │   ├── config.py         # Configuration models
│   │   ├── config_watcher.py # Hot-reload support
│   │   ├── event_server.py   # FastAPI event server
│   │   ├── image_uploader.py # Image upload utilities
│   │   ├── logger.py         # Logging utilities
│   │   ├── message_handler.py # Unified message handling interface
│   │   ├── message_parsers.py # Platform-specific message parsers
│   │   ├── message_queue.py  # Async message queue
│   │   ├── message_tracker.py # Delivery tracking
│   │   ├── provider.py       # Provider abstraction
│   │   ├── templates.py      # Template registry
│   │   └── validation.py     # Config validation
│   ├── plugins/              # Plugin system
│   │   ├── base.py           # BasePlugin class
│   │   ├── config_*.py       # Plugin config utilities
│   │   ├── dependency_checker.py
│   │   ├── feishu_calendar.py # Calendar plugin
│   │   ├── manager.py        # PluginManager
│   │   ├── manifest.py       # Plugin manifest
│   │   ├── rss_subscription.py # RSS subscription plugin
│   │   └── setup_wizard.py   # Setup wizard
│   ├── providers/            # Message providers
│   │   ├── base_http.py      # Base HTTP provider
│   │   ├── feishu.py         # Feishu provider
│   │   ├── feishu_api.py     # Feishu Open Platform API
│   │   ├── qq_event_handler.py # QQ event parsing
│   │   └── qq_napcat.py      # QQ/Napcat provider
│   ├── scheduler/            # Task scheduling
│   │   └── scheduler.py      # TaskScheduler, @job decorator
│   ├── tasks/                # Task execution
│   │   ├── executor.py       # TaskExecutor
│   │   ├── manager.py        # TaskManager
│   │   └── templates.py      # Task templates
│   ├── bot.py                # Main FeishuBot orchestrator
│   ├── cli.py                # Command-line interface
│   └── config_ui.py          # NiceGUI web interface
```

### Core Components

| Component                         | Description                                        |
| --------------------------------- | -------------------------------------------------- |
| **FeishuBot**                     | Main orchestrator coordinating all components      |
| **FeishuWebhookClient**           | Sends messages via webhooks with retry logic       |
| **ChatController**                | Unified multi-platform chat routing and middleware |
| **CommandHandler**                | Chat command system (/help, /reset, /model, etc.)  |
| **TaskScheduler**                 | APScheduler-based job scheduling                   |
| **PluginManager**                 | Plugin discovery, loading, and hot-reload          |
| **AutomationEngine**              | Declarative workflow execution                     |
| **EventServer**                   | FastAPI server for Feishu events                   |
| **TemplateRegistry**              | Message template management                        |
| **AuthService**                   | User authentication and JWT management             |
| **AIAgent**                       | AI responses with tool calling                     |
| **MCPClient**                     | Model Context Protocol support                     |
| **AgentOrchestrator**             | Multi-agent coordination                           |
| **PersistentConversationManager** | Database-backed conversation storage               |
| **MessageQueue**                  | Async message delivery with retry                  |
| **MessageTracker**                | Delivery tracking and deduplication                |
| **CircuitBreaker**                | Fault tolerance for external calls                 |
| **IncomingMessage**               | Universal message representation                   |
| **FeishuMessageParser**           | Parse Feishu event callbacks                       |
| **QQMessageParser**               | Parse OneBot11 events                              |
| **TaskExecutor**                  | Advanced task execution engine                     |
| **TaskManager**                   | Task lifecycle management                          |
| **FeishuProvider**                | Feishu message provider                            |
| **NapcatProvider**                | QQ/Napcat message provider                         |

## 🔗 External Resources

- [Feishu Open Platform](https://open.feishu.cn/)
- [Feishu Cards Documentation](https://open.feishu.cn/document/feishu-cards/feishu-card-overview)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pydantic-AI Documentation](https://ai.pydantic.dev/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [NiceGUI Documentation](https://nicegui.io/)

## 💬 Getting Help

- 📖 Read the full [documentation](getting-started/first-steps.md)
- 🐛 Report issues on [GitHub](https://github.com/AstroAir/feishu-webhook-bot/issues)
- 💬 Ask questions in [Discussions](https://github.com/AstroAir/feishu-webhook-bot/discussions)

---

**Ready to get started?** Head over to [Getting Started](getting-started/first-steps.md)!
