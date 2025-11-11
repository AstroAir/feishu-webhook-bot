# Test Suite for Enhanced YAML Configuration System

This directory contains comprehensive tests for the enhanced YAML configuration system of the Feishu Webhook Bot.

## Test Structure

```
tests/
├── fixtures/              # Test configuration files
│   ├── valid_config.yaml
│   ├── minimal_config.yaml
│   ├── invalid_syntax.yaml
│   └── invalid_schema.yaml
├── mocks/                 # Mock objects for testing
│   ├── __init__.py
│   ├── mock_plugin.py
│   └── mock_scheduler.py
├── conftest.py           # Shared fixtures
├── test_task_executor.py      # Task execution tests
├── test_task_manager.py       # Task management tests
├── test_task_templates.py     # Task template tests
├── test_plugin_config.py      # Plugin configuration tests
├── test_environment_config.py # Environment configuration tests
├── test_validation.py         # Configuration validation tests
├── test_config_watcher.py     # Hot-reload tests
└── test_integration.py        # Integration tests
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

### 1. Task Execution Tests (`test_task_executor.py`)
- Task conditions (time, day, environment, custom)
- Task actions (send_message, plugin_method, http_request, python_code)
- Error handling and retry logic
- Timeout handling

### 2. Task Manager Tests (`test_task_manager.py`)
- Task registration and scheduling
- Task execution (manual and scheduled)
- Task dependencies
- Task status management
- Task reloading

### 3. Task Template Tests (`test_task_templates.py`)
- Template retrieval
- Template instantiation
- Parameter validation
- Parameter substitution

### 4. Plugin Configuration Tests (`test_plugin_config.py`)
- Plugin settings loading
- Plugin priority ordering
- Configuration access methods
- Plugin enable/disable

### 5. Environment Configuration Tests (`test_environment_config.py`)
- Environment loading
- Environment variables
- Configuration overrides
- Active environment selection

### 6. Configuration Validation Tests (`test_validation.py`)
- YAML validation
- JSON schema generation
- Configuration completeness checking
- Improvement suggestions

### 7. Configuration Hot-Reload Tests (`test_config_watcher.py`)
- File watching
- Reload triggers
- Validation before reload
- Debouncing

### 8. Integration Tests (`test_integration.py`)
- End-to-end workflows
- Component integration
- Full bot initialization
- Error handling integration

### 9. AI Integration Tests (`test_ai_integration.py`)
- AI configuration
- Conversation management
- AI agent functionality
- Tool registry
- Bot integration with AI

### 10. Advanced AI Tests (`test_advanced_ai.py`)
- Streaming configuration
- MCP configuration
- Multi-agent configuration
- MCP client functionality
- Agent orchestration
- Specialized agents

### 11. MCP Integration Tests (`test_mcp_integration.py`) **NEW**
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

- **Total Test Files:** 8
- **Total Test Classes:** 43+
- **Total Test Methods:** 150+
- **Expected Coverage:** 80%+

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

