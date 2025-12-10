# Test Suite for Feishu Webhook Bot

This directory contains comprehensive tests for all modules of the Feishu Webhook Bot.

## Test Structure

```text
tests/
├── ai/                          # AI module tests (15 files)
│   ├── test_agent.py            # → src/ai/agent.py
│   ├── test_config.py           # → src/ai/config.py
│   ├── test_conversation.py     # → src/ai/conversation.py
│   ├── test_exceptions.py       # → src/ai/exceptions.py
│   ├── test_mcp_client.py       # → src/ai/mcp_client.py
│   ├── test_multi_agent.py      # → src/ai/multi_agent.py
│   ├── test_retry.py            # → src/ai/retry.py
│   ├── test_task_integration.py # → src/ai/task_integration.py
│   ├── test_tools.py            # → src/ai/tools.py
│   ├── test_ai_capabilities.py  # AI capabilities integration
│   ├── test_ai_features.py      # AI features integration
│   ├── test_ai_integration.py   # AI integration tests
│   ├── test_ai_task_integration.py # AI task integration
│   ├── test_mcp_integration.py  # MCP integration tests
│   └── test_mcp_tool_discovery.py # MCP tool discovery
│
├── auth/                        # Authentication module tests (8 files)
│   ├── test_auth.py             # General auth tests
│   ├── test_database.py         # → src/auth/database.py
│   ├── test_middleware.py       # → src/auth/middleware.py
│   ├── test_models.py           # → src/auth/models.py
│   ├── test_routes.py           # → src/auth/routes.py
│   ├── test_security.py         # → src/auth/security.py
│   ├── test_service.py          # → src/auth/service.py
│   └── test_ui.py               # → src/auth/ui.py
│
├── automation/                  # Automation engine tests (1 file)
│   └── test_engine.py           # → src/automation/engine.py
│
├── core/                        # Core module tests (19 files)
│   ├── test_circuit_breaker.py  # → src/core/circuit_breaker.py
│   ├── test_client.py           # → src/core/client.py
│   ├── test_config.py           # → src/core/config.py
│   ├── test_config_watcher.py   # → src/core/config_watcher.py
│   ├── test_event_server.py     # → src/core/event_server.py
│   ├── test_image_uploader.py   # → src/core/image_uploader.py
│   ├── test_logger.py           # → src/core/logger.py
│   ├── test_message_queue.py    # → src/core/message_queue.py
│   ├── test_message_tracker.py  # → src/core/message_tracker.py
│   ├── test_provider.py         # → src/core/provider.py
│   ├── test_templates.py        # → src/core/templates.py
│   ├── test_validation.py       # → src/core/validation.py
│   └── *_root.py                # Additional tests from root
│
├── plugins/                     # Plugin system tests (7 files)
│   ├── test_base.py             # → src/plugins/base.py
│   ├── test_config.py           # → src/plugins/config_registry.py
│   ├── test_config_schema.py    # → src/plugins/config_schema.py
│   ├── test_feishu_calendar.py  # → src/plugins/feishu_calendar.py
│   ├── test_manager.py          # → src/plugins/manager.py
│   ├── test_plugins.py          # General plugin tests
│   └── test_setup_wizard.py     # → src/plugins/setup_wizard.py
│
├── providers/                   # Provider tests (2 files)
│   ├── test_providers.py        # → src/providers/feishu.py, qq_napcat.py
│   └── test_multi_provider.py   # Multi-provider tests
│
├── scheduler/                   # Scheduler tests (1 file)
│   └── test_scheduler.py        # → src/scheduler/scheduler.py
│
├── tasks/                       # Task system tests (3 files)
│   ├── test_executor.py         # → src/tasks/executor.py
│   ├── test_manager.py          # → src/tasks/manager.py
│   └── test_templates.py        # → src/tasks/templates.py
│
├── fixtures/                    # Test configuration files
├── mocks/                       # Mock objects for testing
├── conftest.py                  # Shared fixtures
├── test_bot.py                  # → src/bot.py
├── test_cli.py                  # → src/cli.py
├── test_environment_config.py   # Environment configuration
└── test_integration.py          # Integration tests
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock pyyaml watchdog
```

### Run All Tests

```bash
# From project root
pytest tests/ -v

# Or use the test runner script
python run_tests.py
```

### Run Specific Test File

```bash
# Run task executor tests
pytest tests/test_task_executor.py -v

# Or use the test runner
python run_tests.py task_executor
```

### Run Specific Test Class

```bash
pytest tests/test_task_executor.py::TestTaskConditions -v
```

### Run Specific Test Method

```bash
pytest tests/test_task_executor.py::TestTaskConditions::test_time_range_condition_within_range -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/ -v --cov=src/feishu_webhook_bot --cov-report=html

# View coverage report
# Open htmlcov/index.html in your browser
```

### Run with Verbose Output

```bash
pytest tests/ -vv
```

### Run and Stop on First Failure

```bash
pytest tests/ -x
```

### Run Only Failed Tests

```bash
# Run tests and save failures
pytest tests/ --lf
```

### Run MCP Integration Tests

```bash
# All MCP tests (excluding trio backend)
pytest tests/test_mcp_integration.py -v -k "not trio"

# Only configuration tests
pytest tests/test_mcp_integration.py::TestMCPConfig -v

# Only tests that don't require API key
pytest tests/test_mcp_integration.py -v -k "not Agent"

# Only tests that require API key (set OPENAI_API_KEY first)
export OPENAI_API_KEY='your-key'
pytest tests/test_mcp_integration.py::TestAIAgentMCPIntegration -v
```

### Run AI Integration Tests

```bash
# All AI tests
pytest tests/test_ai_integration.py tests/test_advanced_ai.py -v -k "not trio"

# Tests that don't require API key
pytest tests/test_ai_integration.py -v -k "not Agent"

# Tests that require API key
export OPENAI_API_KEY='your-key'
pytest tests/test_ai_integration.py tests/test_advanced_ai.py -v
```

## Test Categories

### AI Module Tests (`tests/ai/`)

#### Conversation Tests (`test_conversation.py`)
- ConversationState creation and lifecycle
- Message management and token tracking
- Conversation expiration
- Analytics and export/import
- ConversationManager operations
- Cleanup task management
- **Concurrent access and thread safety**
- **Edge cases (unicode, empty values, large data)**
- **Advanced analytics (duration, context keys)**

#### Tools Tests (`test_tools.py`)
- ai_tool decorator
- SearchCache functionality
- ToolRegistry operations
- Built-in tools (calculate, format_json, convert_units, etc.)
- **web_search with caching and retry logic**
- **get_search_cache_stats and clear_search_cache utilities**
- **Edge cases (unicode, case sensitivity, spaces)**
- **Advanced ToolRegistry (permissions, categories, stats)**

#### Retry Tests (`test_retry.py`)
- CircuitBreaker state transitions (CLOSED → OPEN → HALF_OPEN)
- Sync and async circuit breaker operations
- Exponential backoff decorator
- Retry logic with jitter
- **Custom exception types**
- **Recovery and reset behavior**
- **Concurrent async operations**
- **Edge cases (zero threshold, high threshold, short timeout)**

#### Multi-Agent Tests (`test_multi_agent.py`)
- AgentMessage and AgentResult models
- SpecializedAgent and subclasses
- AgentOrchestrator initialization
- Sequential, concurrent, hierarchical orchestration
- **Advanced orchestration (partial failures, long messages)**
- **Unicode content handling**
- **Context preservation**
- **Custom agent registration**

#### Exception Tests (`test_exceptions.py`)
- AIError base exception
- AIServiceUnavailableError
- ToolExecutionError
- ConversationNotFoundError
- ModelResponseError
- TokenLimitExceededError
- RateLimitError
- ConfigurationError

### Auth Module Tests (`tests/auth/`)

#### Security Tests (`test_security.py`)
- Password hashing with bcrypt
- Password verification
- Password strength validation
- JWT token creation and decoding
- Security configuration

### Core Module Tests (`tests/core/`)

#### Template Tests (`test_templates.py`)
- RenderedTemplate dataclass
- TemplateRegistry initialization
- Template listing and retrieval
- Template rendering with different engines
- Error handling

#### Image Uploader Tests (`test_image_uploader.py`)
- FeishuPermissionChecker utilities
- FeishuImageUploader initialization
- Token management
- Image upload operations
- Permission error handling

### Task System Tests (Root Level)

#### Task Execution Tests (`test_task_executor.py`)
- Task conditions (time, day, environment, custom)
- Task actions (send_message, plugin_method, http_request, python_code)
- Error handling and retry logic
- Timeout handling

#### Task Manager Tests (`test_task_manager.py`)
- Task registration and scheduling
- Task execution (manual and scheduled)
- Task dependencies
- Task status management
- Task reloading

#### Task Template Tests (`test_task_templates.py`)
- Template retrieval
- Template instantiation
- Parameter validation
- Parameter substitution

### Plugin System Tests (Root Level)

#### Plugin Base Tests (`test_plugin_base.py`)
- PluginMetadata dataclass
- BasePlugin abstract class
- Provider access
- Lifecycle hooks
- Job registration
- Configuration access
- Event handling

#### Plugin Manager Tests (`test_plugin_manager.py`)
- Plugin discovery
- Plugin loading from files
- Lifecycle management (enable/disable)
- Hot-reload functionality
- Job registration with scheduler
- Multi-provider support
- Event dispatching

#### Plugin Configuration Tests (`test_plugin_config.py`)
- Plugin settings loading
- Plugin priority ordering
- Configuration access methods
- Plugin enable/disable

### Provider Tests (Root Level)

#### Provider Tests (`test_providers.py`)
- BaseProvider interface
- SendResult factory methods
- MessageType enum
- ProviderConfig validation
- ProviderRegistry singleton
- FeishuProvider implementation
- NapcatProvider implementation
- HMAC signature generation
- Retry and circuit breaker integration

### Automation Tests (Root Level)

#### Automation Engine Tests (`test_automation_engine.py`)
- AutomationEngine lifecycle (start/shutdown)
- Schedule-based triggers
- Event-based triggers
- Action execution
- Context handling and merging
- Template rendering
- HTTP request execution

### Configuration Tests (Root Level)

#### Environment Configuration Tests (`test_environment_config.py`)
- Environment loading
- Environment variables
- Configuration overrides
- Active environment selection

#### Configuration Validation Tests (`test_validation.py`)
- YAML validation
- JSON schema generation
- Configuration completeness checking
- Improvement suggestions

#### Configuration Hot-Reload Tests (`test_config_watcher.py`)
- File watching
- Reload triggers
- Validation before reload
- Debouncing

### Integration Tests (Root Level)

#### Integration Tests (`test_integration.py`)
- End-to-end workflows
- Component integration
- Full bot initialization
- Error handling integration

#### AI Integration Tests (`test_ai_integration.py`)
- AI configuration
- Conversation management
- AI agent functionality
- Tool registry
- Bot integration with AI

#### Advanced AI Tests (`test_advanced_ai.py`)
- Streaming configuration
- MCP configuration
- Multi-agent configuration
- MCP client functionality
- Agent orchestration
- Specialized agents

#### MCP Integration Tests (`test_mcp_integration.py`)
- MCP configuration (stdio, HTTP, SSE transports)
- MCP client initialization and lifecycle
- MCP transport types
- MCP error handling
- AI agent MCP integration
- MCP with built-in tools
- Lazy MCP initialization
- Graceful degradation

## Writing New Tests

### Test File Template

```python
"""Tests for [component name]."""

import pytest
from feishu_webhook_bot.core.config import BotConfig


@pytest.fixture
def sample_config():
    """Create a sample configuration."""
    return BotConfig(
        webhooks=[{"name": "default", "url": "https://example.com/webhook"}]
    )


class TestComponentName:
    """Test [component] functionality."""

    def test_something(self, sample_config):
        """Test that something works."""
        # Arrange
        expected = "value"
        
        # Act
        result = sample_config.some_method()
        
        # Assert
        assert result == expected
```

### Best Practices

1. **Use Descriptive Names** - Test names should clearly describe what they test
2. **Follow AAA Pattern** - Arrange, Act, Assert
3. **One Assertion Per Test** - Keep tests focused
4. **Use Fixtures** - Reuse common setup code
5. **Mock External Dependencies** - Isolate the code under test
6. **Test Both Success and Failure** - Cover happy path and error cases
7. **Use Parametrize** - Test multiple scenarios efficiently

### Example: Parametrized Test

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("dev", "development"),
    ("prod", "production"),
    ("staging", "staging"),
])
def test_environment_expansion(input, expected):
    """Test environment name expansion."""
    result = expand_environment_name(input)
    assert result == expected
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ -v --cov=src/feishu_webhook_bot
```

## Troubleshooting

### Tests Fail with Import Errors

Make sure the package is installed in development mode:
```bash
pip install -e .
```

### Tests Fail with Missing Dependencies

Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock pyyaml watchdog
```

### Tests Hang or Timeout

Some tests involve file watching and delays. Increase timeout:
```bash
pytest tests/ --timeout=300
```

### Coverage Report Not Generated

Install coverage:
```bash
pip install pytest-cov
```

### Trio Backend Errors (MCP/AI Tests)

**Error:** `ModuleNotFoundError: No module named 'trio'`

**Solution:** Run tests with `-k "not trio"`:
```bash
pytest tests/ -v -k "not trio"
```

### Many Tests Skipped (MCP/AI Tests)

**Issue:** Tests skip with "OPENAI_API_KEY not set"

**Solution:** Set the API key to run all tests:
```bash
export OPENAI_API_KEY='your-openai-api-key'
pytest tests/test_mcp_integration.py -v
```

### MCP Tests Failing

**Error:** `RuntimeError: pydantic-ai MCP support not available`

**Solution:** Install MCP support:
```bash
pip install 'pydantic-ai-slim[mcp]'
```

### Test Import Errors for `tests.mocks`

**Error:** `ModuleNotFoundError: No module named 'tests'`

**Solution:** Run pytest from project root:
```bash
cd /path/to/feishu-webhook-bot
pytest tests/ -v
```

## Test Metrics

- **Total Test Files:** 50+
- **Total Test Classes:** 100+
- **Total Test Methods:** 500+
- **Expected Coverage:** 85%+

### AI Module Test Coverage

| Module | Test File | Test Classes | Key Areas |
|--------|-----------|--------------|-----------|
| `conversation.py` | `test_conversation.py` | 8 | State, Manager, Concurrency, Analytics |
| `tools.py` | `test_tools.py` | 10 | Decorator, Cache, Registry, Web Search |
| `retry.py` | `test_retry.py` | 6 | CircuitBreaker, Retry Decorator, Edge Cases |
| `multi_agent.py` | `test_multi_agent.py` | 8 | Models, Agents, Orchestrator, Modes |
| `exceptions.py` | `test_exceptions.py` | 8 | All exception types |
| `config.py` | `test_config.py` | 5 | All config classes |
| `task_integration.py` | `test_task_integration.py` | 6 | Executor, Prompts, Config |
| `agent.py` | `test_agent.py` | 5 | Agent, Dependencies, Metrics |
| `mcp_client.py` | `test_mcp_client.py` | 4 | Client, Transport, Discovery |

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update this README if needed

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## Support

For issues or questions about tests:
1. Check test output for error messages
2. Review test implementation in the relevant file
3. Check TESTS_IMPLEMENTATION_SUMMARY.md for details
4. Consult TESTING_GUIDE.md for testing strategy

