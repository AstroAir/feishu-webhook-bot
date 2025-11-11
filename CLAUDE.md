# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Feishu Webhook Bot is a production-ready Python framework for building Feishu (Lark) webhook bots with advanced features including:
- Message sending (text, rich text, interactive cards, images)
- Task scheduling and automation workflows
- Extensible plugin system with hot-reload
- AI integration with multi-turn conversations and tool calling
- Event server for handling incoming webhooks
- Authentication system with JWT tokens
- MCP (Model Context Protocol) support for standardized tool access

## Development Commands

### Setup and Installation

```bash
# Install using uv (recommended)
uv sync --all-groups

# Or using pip
pip install -e .
```

### Running Tests

```bash
# Run all tests
uv run pytest -q

# Run specific test file
uv run pytest tests/test_bot.py -v

# Run with coverage
uv run pytest --cov=src/feishu_webhook_bot --cov-report=html

# Run AI/MCP tests (requires OPENAI_API_KEY)
export OPENAI_API_KEY="your-key"
uv run pytest tests/test_ai_integration.py tests/test_mcp_integration.py -v -k "not trio"
```

### Code Quality

```bash
# Format code
uv run black .

# Lint code
uv run ruff check .

# Type check
uv run mypy .

# Run all checks (CI pipeline)
uv run python scripts/tasks.py ci
# or
uv run ruff check . ; uv run black --check . ; uv run mypy . ; uv run pytest -q ; uv build
```

### Task Runner

Cross-platform task runner available via:
```bash
# Python (all platforms)
uv run python scripts/tasks.py [task]

# Bash (Linux/macOS)
scripts/task.sh [task]

# PowerShell (Windows)
scripts/task.ps1 [task]
```

Available tasks: `setup`, `lint`, `format`, `typecheck`, `test`, `build`, `docs:build`, `docs:serve`, `ci`

### Documentation

```bash
# Build docs
uv run mkdocs build --strict

# Serve locally
uv run mkdocs serve -a localhost:8000
```

### Running the Bot

```bash
# Initialize config
feishu-webhook-bot init --output config.yaml

# Start bot
feishu-webhook-bot start --config config.yaml

# Launch Web UI
feishu-webhook-bot webui --config config.yaml --host 127.0.0.1 --port 8080

# Send test message
feishu-webhook-bot send --webhook "https://..." --text "Hello!"
```

## Architecture

### Core Components

The framework follows a modular architecture with these key components:

1. **FeishuBot** (`bot.py`) - Main orchestrator that coordinates all subsystems
   - Initializes and manages lifecycle of all components
   - Handles signal-based graceful shutdown
   - Provides unified API for sending messages

2. **FeishuWebhookClient** (`core/client.py`) - HTTP client for Feishu API
   - Sends messages via webhooks (text, rich text, cards, images)
   - `CardBuilder` class for fluent interactive card construction
   - Retry logic with exponential backoff
   - HMAC-SHA256 webhook signing support

3. **TaskScheduler** (`scheduler/scheduler.py`) - Job scheduling wrapper around APScheduler
   - Supports cron and interval-based scheduling
   - Persistent or in-memory job storage
   - Timezone-aware scheduling

4. **PluginManager** (`plugins/manager.py`) - Plugin system with hot-reload
   - Discovers plugins in configured directory
   - Manages plugin lifecycle (load, enable, disable, unload)
   - File watcher for automatic plugin reload
   - Each plugin extends `BasePlugin` with lifecycle hooks

5. **AutomationEngine** (`automation/engine.py`) - Declarative workflow execution
   - Schedule-based and event-based triggers
   - Actions: send messages, HTTP requests, plugin methods, Python code
   - Template rendering with variable substitution
   - Condition evaluation for workflow control

6. **TaskManager** (`tasks/manager.py`) - Automated task execution
   - Task scheduling with conditions (time, day, environment)
   - Task dependencies and retry logic
   - Integration with plugins and AI agent
   - Task templates for reusable configurations

7. **EventServer** (`core/event_server.py`) - FastAPI server for incoming webhooks
   - Receives and validates Feishu events
   - Token verification and signature validation
   - Dispatches events to plugins and automation engine
   - Integrates with AI agent for chat messages

8. **AIAgent** (`ai/agent.py`) - AI-powered conversational capabilities
   - Multi-turn conversations with context management
   - Tool/function calling (web search, calculations, etc.)
   - Streaming responses with debouncing
   - MCP integration for standardized tool access
   - Multi-agent orchestration (A2A pattern)
   - Supports OpenAI, Anthropic, Google, Groq providers

### Configuration System

Configuration uses Pydantic models (`core/config.py`) with:
- YAML/JSON file support
- Environment variable expansion: `${VAR_NAME}`
- Validation with clear error messages
- Hot-reload capability via file watcher
- Nested configuration for all subsystems

Key config sections:
- `webhooks`: List of webhook configurations
- `scheduler`: APScheduler settings
- `plugins`: Plugin directory and hot-reload settings
- `automations`: Declarative workflow rules
- `tasks`: Automated task definitions
- `templates`: Reusable message templates
- `event_server`: Incoming webhook server config
- `ai`: AI agent configuration with MCP support
- `logging`: Log level, file, rotation settings
- `http`: Default timeout and retry policy

### Plugin Development

Plugins inherit from `BasePlugin` (`plugins/base.py`) and override:
- `metadata()`: Return plugin info (name, version, description, author)
- `on_load()`: Called when plugin is loaded
- `on_enable()`: Called when bot starts and plugin is activated
- `on_disable()`: Called when bot stops or plugin is deactivated
- `on_unload()`: Called before hot-reload

Plugins have access to:
- `self.client`: Default webhook client
- `self.config`: Bot configuration
- `self.scheduler`: Task scheduler
- `self.register_job()`: Schedule periodic tasks
- `self.logger`: Plugin-specific logger

### AI Integration

The AI system (`ai/`) provides:
- **ConversationManager**: Multi-turn dialogue with context cleanup
- **ToolRegistry**: Register custom tools for AI to use
- **AIAgent**: Main agent orchestrator with pydantic-ai integration
- **MCPClient**: Model Context Protocol client for stdio/HTTP/SSE transports
- **AgentOrchestrator**: Multi-agent coordination (sequential/concurrent/hierarchical)
- **AITaskExecutor**: Execute AI-powered tasks in automation workflows

AI features:
- Streaming responses with configurable debouncing
- Output validation with automatic retry
- Circuit breaker for rate limiting
- Web search via DuckDuckGo
- Custom tool registration
- MCP server integration (Python, filesystem, etc.)
- Multi-provider support with provider-specific configs

### Testing Strategy

Tests use pytest with these patterns:
- `tests/test_*.py`: Test files organized by component
- `tests/fixtures/`: Test configuration files
- `tests/mocks/`: Mock objects for testing
- `conftest.py`: Shared fixtures across tests

Test categories:
- Unit tests: Core components, configuration, validation
- Integration tests: Bot initialization, plugin system, automation
- AI tests: Agent, conversation, tools, MCP (requires API key)
- End-to-end tests: Full workflows with mocked HTTP

Run tests from project root to ensure proper module imports.

## Important Patterns

### Message Sending

Always use `CardBuilder` for interactive cards:
```python
from feishu_webhook_bot.core.client import CardBuilder

card = (
    CardBuilder()
    .set_header("Title", template="blue")
    .add_markdown("**Bold** text")
    .add_divider()
    .add_button("Click", url="https://...")
    .build()
)
client.send_card(card)
```

### Task Scheduling in Plugins

```python
class MyPlugin(BasePlugin):
    def on_enable(self):
        # Interval-based
        self.register_job(self.my_task, trigger='interval', minutes=5)

        # Cron-based
        self.register_job(self.daily_task, trigger='cron', hour='9', minute='0')
```

### Environment Variable Expansion

In YAML configs:
```yaml
webhooks:
  - name: default
    url: ${FEISHU_WEBHOOK_URL}
    secret: ${FEISHU_WEBHOOK_SECRET}
```

### Error Handling

Components use structured logging with Rich formatting. Always:
- Use `get_logger(__name__)` from `core.logger`
- Log errors with `exc_info=True` for stack traces
- Raise specific exceptions with clear messages
- Handle exceptions at component boundaries

### AI Agent Usage

```python
# In automation workflows
actions:
  - type: ai_task
    prompt: "Analyze this data: ${data}"
    model: "openai:gpt-4o"

# Programmatically
agent = AIAgent(ai_config)
agent.start()
response = await agent.chat("user123", "What's the weather?")
await agent.stop()
```

### MCP Integration

Configure MCP servers in `config.yaml`:
```yaml
ai:
  enabled: true
  mcp:
    enabled: true
    servers:
      - name: python-runner
        command: uv
        args: run mcp-run-python stdio
      - name: weather-api
        url: http://localhost:3001/mcp  # HTTP transport
```

Requires: `pip install 'pydantic-ai-slim[mcp]'`

## Common Issues

### Plugin Not Loading
- Ensure plugin file is in configured `plugin_dir`
- Plugin class must extend `BasePlugin`
- Plugin must have a unique `name` attribute
- Check logs for import errors

### Hot Reload Not Working
- Verify `auto_reload: true` in plugins config
- Check file watcher is running (logs show "watching directory")
- File changes may have debounce delay

### AI Agent Failures
- Verify API key is set: `echo $OPENAI_API_KEY`
- Check model string format: `provider:model-name`
- Ensure pydantic-ai dependencies installed
- For MCP: install with `pip install 'pydantic-ai-slim[mcp]'`

### Test Import Errors
- Always run pytest from project root
- Install in development mode: `pip install -e .`
- For MCP tests, skip trio backend: `-k "not trio"`

### Configuration Validation Errors
- Use `uv run python -c "from feishu_webhook_bot import FeishuBot; FeishuBot.from_config('config.yaml')"` to validate
- Check Pydantic error messages for field details
- Ensure all required fields are present

## Key Files Reference

- `src/feishu_webhook_bot/bot.py` - Main bot orchestrator
- `src/feishu_webhook_bot/core/config.py` - Configuration models and loading
- `src/feishu_webhook_bot/core/client.py` - Webhook client and CardBuilder
- `src/feishu_webhook_bot/plugins/base.py` - Plugin base class
- `src/feishu_webhook_bot/plugins/manager.py` - Plugin lifecycle management
- `src/feishu_webhook_bot/scheduler/scheduler.py` - Task scheduling
- `src/feishu_webhook_bot/automation/engine.py` - Workflow automation
- `src/feishu_webhook_bot/tasks/manager.py` - Task management
- `src/feishu_webhook_bot/tasks/executor.py` - Task execution logic
- `src/feishu_webhook_bot/core/event_server.py` - Incoming webhook server
- `src/feishu_webhook_bot/ai/agent.py` - AI agent implementation
- `src/feishu_webhook_bot/ai/mcp_client.py` - MCP client for tool integration
- `src/feishu_webhook_bot/ai/multi_agent.py` - Multi-agent orchestration
- `src/feishu_webhook_bot/cli.py` - Command-line interface
- `pyproject.toml` - Project metadata and dependencies
- `tests/conftest.py` - Shared test fixtures

## Contributing

When making changes:
1. Write tests first (TDD approach preferred)
2. Run `uv run python scripts/tasks.py ci` before committing
3. Ensure all tests pass and coverage is maintained
4. Update documentation if adding new features
5. Follow existing code patterns and style
