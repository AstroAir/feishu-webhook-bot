# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Feishu Webhook Bot is a Python framework for building Feishu (Lark) webhook bots with:

- Message sending (text, rich text, interactive cards, images)
- Task scheduling with APScheduler
- Extensible plugin system with hot-reload
- AI integration via pydantic-ai (OpenAI, Anthropic, Google, Groq)
- MCP (Model Context Protocol) for standardized tool access
- FastAPI event server for incoming webhooks
- Authentication with JWT tokens

## Development Commands

### Setup

```bash
uv sync --all-groups        # Install all dependencies
pip install -e .            # Alternative: pip editable install
```

### Testing

```bash
uv run pytest -q                              # Run all tests
uv run pytest tests/test_bot.py -v            # Run specific test file
uv run pytest tests/test_bot.py::test_name -v # Run single test function
uv run pytest -m "not slow"                   # Skip slow tests
uv run pytest --cov=src/feishu_webhook_bot    # With coverage

# AI/MCP tests require API key
export OPENAI_API_KEY="your-key"
uv run pytest tests/test_ai_integration.py -v -k "not trio"
```

### Code Quality

```bash
uv run black .                    # Format
uv run ruff check .               # Lint
uv run mypy .                     # Type check
uv run python scripts/tasks.py ci # Run all checks (CI pipeline)
```

### Task Runner

```bash
uv run python scripts/tasks.py [task]  # Python (all platforms)
scripts/task.sh [task]                  # Bash (Linux/macOS)
scripts/task.ps1 [task]                 # PowerShell (Windows)
```

Tasks: `setup`, `lint`, `format`, `typecheck`, `test`, `build`, `docs:build`, `docs:serve`, `ci`

### Running the Bot

```bash
feishu-webhook-bot init --output config.yaml   # Initialize config
feishu-webhook-bot start --config config.yaml  # Start bot
feishu-webhook-bot webui --config config.yaml  # Launch Web UI
feishu-webhook-bot send --webhook "url" --text "Hello!"  # Send message
```

## Architecture

### File Layout (src/feishu_webhook_bot)

```text
feishu_webhook_bot/
├── __init__.py
├── __main__.py
├── ai/
│   ├── __init__.py
│   ├── agent.py
│   ├── config.py
│   ├── conversation.py
│   ├── exceptions.py
│   ├── mcp_client.py
│   ├── multi_agent.py
│   ├── retry.py
│   ├── task_integration.py
│   └── tools.py
├── auth/
│   ├── __init__.py
│   ├── database.py
│   ├── middleware.py
│   ├── models.py
│   ├── routes.py
│   ├── security.py
│   ├── service.py
│   └── ui.py
├── automation/
│   ├── __init__.py
│   └── engine.py
├── core/
│   ├── __init__.py
│   ├── circuit_breaker.py
│   ├── client.py
│   ├── config.py
│   ├── config_watcher.py
│   ├── event_server.py
│   ├── image_uploader.py
│   ├── logger.py
│   ├── message_queue.py
│   ├── message_tracker.py
│   ├── provider.py
│   ├── templates.py
│   └── validation.py
├── plugins/
│   ├── __init__.py
│   ├── base.py
│   ├── feishu_calendar.py
│   └── manager.py
├── providers/
│   ├── __init__.py
│   ├── base_http.py
│   ├── feishu.py
│   └── qq_napcat.py
├── scheduler/
│   ├── __init__.py
│   └── scheduler.py
├── tasks/
│   ├── __init__.py
│   ├── executor.py
│   ├── manager.py
│   └── templates.py
├── bot.py
├── cli.py
├── config_ui.py
└── __init__.py
```

### Core Components

1. **FeishuBot** (`bot.py`) - Main orchestrator with graceful shutdown
2. **FeishuWebhookClient** (`core/client.py`) - HTTP client + `CardBuilder`, retries, HMAC signing
3. **TaskScheduler** (`scheduler/scheduler.py`) - APScheduler wrapper for cron/interval jobs
4. **PluginManager** (`plugins/manager.py`) - Plugin lifecycle and hot-reload
5. **AutomationEngine** (`automation/engine.py`) - Declarative workflows (schedule/event triggers)
6. **TaskManager** (`tasks/manager.py`) - Task execution with dependencies/retries and AI hooks
7. **EventServer** (`core/event_server.py`) - FastAPI webhook ingress with verification
8. **AuthService** (`auth/service.py`) - Registration/login, JWT issuance, password policies
9. **AIAgent & MCPClient** (`ai/agent.py`, `ai/mcp_client.py`) - Multi-turn AI, tool calling, streaming, MCP toolsets
10. **MessageQueue & MessageTracker** (`core/message_queue.py`, `core/message_tracker.py`) - Delivery coordination and deduplication
11. **CircuitBreaker** (`core/circuit_breaker.py`) - Resilience for outbound calls

### Configuration System

Pydantic models in `core/config.py` with YAML/JSON support and environment variable expansion (`${VAR_NAME}`).

Key sections: `webhooks`, `scheduler`, `plugins`, `automations`, `tasks`, `templates`, `event_server`, `ai`, `logging`, `http`

### Plugin Development

Plugins extend `BasePlugin` (`plugins/base.py`):

- `metadata()` - Return plugin info
- `on_load()` / `on_unload()` - Load/unload hooks
- `on_enable()` / `on_disable()` - Activation hooks
- Access: `self.client`, `self.config`, `self.scheduler`, `self.register_job()`, `self.logger`

### AI System (`ai/`)

- **ConversationManager** - Multi-turn dialogue with context cleanup
- **ToolRegistry** - Custom tool registration
- **AIAgent** - Main orchestrator with streaming and output validation
- **MCPClient** - MCP client for stdio/HTTP/SSE transports
- **AgentOrchestrator** - Multi-agent coordination (sequential/concurrent/hierarchical)

## Important Patterns

### CardBuilder Usage

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

### Plugin Job Registration

```python
def on_enable(self):
    self.register_job(self.my_task, trigger='interval', minutes=5)
    self.register_job(self.daily_task, trigger='cron', hour='9', minute='0')
```

### Error Handling

- Use `get_logger(__name__)` from `core.logger`
- Log errors with `exc_info=True` for stack traces
- Handle exceptions at component boundaries

## Testing

Test organization:

- `tests/test_*.py` - Test files by component
- `tests/fixtures/` - Test configuration files
- `tests/conftest.py` - Shared fixtures

Test markers:

- `@pytest.mark.slow` - Marks slow tests (skip with `-m "not slow"`)

Always run pytest from project root. For MCP tests, use `-k "not trio"` to skip trio backend tests.

## Common Issues

### Plugin Not Loading

- Plugin class must extend `BasePlugin` with unique `name` attribute
- Check logs for import errors

### AI Agent Failures

- Verify API key: `echo $OPENAI_API_KEY`
- Model format: `provider:model-name` (e.g., `openai:gpt-4o`)
- MCP requires: `pip install 'pydantic-ai-slim[mcp]'`

### Configuration Validation

```bash
uv run python -c "from feishu_webhook_bot import FeishuBot; FeishuBot.from_config('config.yaml')"
```

## Key Files

- `src/feishu_webhook_bot/bot.py` - Main orchestrator
- `src/feishu_webhook_bot/core/config.py` - Configuration models
- `src/feishu_webhook_bot/core/client.py` - Webhook client & CardBuilder
- `src/feishu_webhook_bot/plugins/base.py` - Plugin base class
- `src/feishu_webhook_bot/ai/agent.py` - AI agent
- `src/feishu_webhook_bot/cli.py` - CLI interface
- `tests/conftest.py` - Test fixtures
