# Testing Guide for Enhanced YAML Configuration System

This document outlines the testing strategy for the enhanced YAML configuration system.

## Test Categories

### 1. Task Execution Tests

**File:** `tests/test_task_executor.py`

Test cases:
- ✅ Task execution with send_message action
- ✅ Task execution with plugin_method action
- ✅ Task execution with http_request action
- ✅ Task execution with python_code action
- ✅ Task condition checking (time_range, day_of_week, environment, custom)
- ✅ Task error handling and retry logic
- ✅ Task timeout handling
- ✅ Task context and parameter passing
- ✅ Multiple actions in sequence
- ✅ Action result saving and context updates

### 2. Task Manager Tests

**File:** `tests/test_task_manager.py`

Test cases:
- ✅ Task registration with scheduler
- ✅ Task execution via scheduler
- ✅ Concurrent execution limits
- ✅ Task priority handling
- ✅ Task dependencies (depends_on, run_after)
- ✅ Task enable/disable
- ✅ Task status reporting
- ✅ Task list retrieval
- ✅ Manual task execution (execute_task_now)
- ✅ Task reload

### 3. Task Template Tests

**File:** `tests/test_task_templates.py`

Test cases:
- ✅ Template creation
- ✅ Template instantiation
- ✅ Parameter substitution
- ✅ Parameter validation
- ✅ Required parameter checking
- ✅ Parameter type checking
- ✅ Template override application
- ✅ Template listing

### 4. Plugin Configuration Tests

**File:** `tests/test_plugin_config.py`

Test cases:
- ✅ Plugin settings loading
- ✅ Plugin priority ordering
- ✅ Plugin enable/disable via configuration
- ✅ get_config_value() method
- ✅ get_all_config() method
- ✅ Plugin settings with defaults
- ✅ Multiple plugins with different settings

### 5. Environment Configuration Tests

**File:** `tests/test_environment_config.py`

Test cases:
- ✅ Environment loading
- ✅ Environment variable injection
- ✅ Configuration overrides
- ✅ Active environment selection
- ✅ Environment variable expansion
- ✅ Multiple environments
- ✅ Environment-specific task conditions

### 6. Configuration Validation Tests

**File:** `tests/test_validation.py`

Test cases:
- ✅ Valid configuration validation
- ✅ Invalid configuration detection
- ✅ YAML syntax error detection
- ✅ Pydantic validation error reporting
- ✅ JSON schema generation
- ✅ Configuration completeness checking
- ✅ Configuration improvement suggestions
- ✅ Template configuration generation

### 7. Configuration Hot-Reload Tests

**File:** `tests/test_config_watcher.py`

Test cases:
- ✅ File modification detection
- ✅ Configuration reload on change
- ✅ Validation before reload
- ✅ Reload debouncing
- ✅ Plugin reload on config change
- ✅ Task reload on config change
- ✅ Invalid configuration rejection
- ✅ Watcher start/stop

### 8. Integration Tests

**File:** `tests/test_integration.py`

Test cases:
- ✅ Bot initialization with enhanced config
- ✅ Task manager integration with scheduler
- ✅ Task manager integration with plugin system
- ✅ Config watcher integration with bot
- ✅ Task execution with plugin method calls
- ✅ Environment-based task execution
- ✅ Template-based task creation
- ✅ Full workflow: config → validation → load → execute

## Test Data

### Sample Configuration Files

Create test configuration files in `tests/fixtures/`:

1. **valid_config.yaml** - Valid configuration with all features
2. **invalid_syntax.yaml** - Invalid YAML syntax
3. **invalid_schema.yaml** - Valid YAML but invalid schema
4. **minimal_config.yaml** - Minimal valid configuration
5. **tasks_config.yaml** - Configuration with various task types
6. **templates_config.yaml** - Configuration with task templates
7. **environments_config.yaml** - Configuration with environments
8. **plugins_config.yaml** - Configuration with plugin settings

### Sample Task Definitions

```python
# tests/fixtures/sample_tasks.py

SIMPLE_TASK = {
    "name": "simple_task",
    "enabled": True,
    "schedule": {
        "mode": "interval",
        "arguments": {"minutes": 5}
    },
    "actions": [
        {
            "type": "send_message",
            "webhook": "default",
            "message": "Test message"
        }
    ],
    "error_handling": {
        "on_failure": "log",
        "retry_on_failure": False
    }
}

COMPLEX_TASK = {
    "name": "complex_task",
    "enabled": True,
    "cron": "0 9 * * *",
    "conditions": [
        {"type": "day_of_week", "days": ["monday", "friday"]},
        {"type": "environment", "environment": "production"}
    ],
    "actions": [
        {
            "type": "http_request",
            "request": {
                "method": "GET",
                "url": "https://api.example.com/data",
                "save_as": "api_data"
            }
        },
        {
            "type": "plugin_method",
            "plugin": "test-plugin",
            "method": "process_data",
            "args": ["${api_data}"],
            "save_as": "processed"
        },
        {
            "type": "send_message",
            "webhook": "default",
            "message": "Processed: ${processed}"
        }
    ],
    "error_handling": {
        "on_failure": "notify",
        "retry_on_failure": True,
        "max_retries": 3,
        "retry_delay": 60
    },
    "timeout": 300,
    "priority": 50
}
```

## Mock Objects

### Mock Plugin

```python
# tests/mocks/mock_plugin.py

from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class MockPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin"
        )
    
    def process_data(self, data):
        return {"processed": True, "data": data}
    
    def get_stats(self):
        return {"cpu": 50, "memory": 60}
```

### Mock Scheduler

```python
# tests/mocks/mock_scheduler.py

class MockScheduler:
    def __init__(self):
        self.jobs = {}
    
    def add_job(self, func, trigger, job_id, **kwargs):
        self.jobs[job_id] = {
            "func": func,
            "trigger": trigger,
            "kwargs": kwargs
        }
    
    def remove_job(self, job_id):
        if job_id in self.jobs:
            del self.jobs[job_id]
    
    def get_job(self, job_id):
        return self.jobs.get(job_id)
```

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Category

```bash
pytest tests/test_task_executor.py
pytest tests/test_task_manager.py
pytest tests/test_validation.py
```

### Run with Coverage

```bash
pytest --cov=src/feishu_webhook_bot --cov-report=html tests/
```

### Run Integration Tests Only

```bash
pytest tests/test_integration.py -v
```

## Test Coverage Goals

Target coverage for each module:

- `tasks/executor.py` - 90%+
- `tasks/manager.py` - 90%+
- `tasks/templates.py` - 90%+
- `core/validation.py` - 85%+
- `core/config_watcher.py` - 85%+
- `plugins/base.py` (new methods) - 90%+
- `plugins/manager.py` (new code) - 90%+
- `bot.py` (new methods) - 85%+

## Continuous Integration

Add to CI pipeline:

```yaml
# .github/workflows/test.yml

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
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          pytest --cov=src/feishu_webhook_bot --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Manual Testing Checklist

Before release, manually test:

- [ ] Create a task with interval scheduling
- [ ] Create a task with cron scheduling
- [ ] Test task with send_message action
- [ ] Test task with plugin_method action
- [ ] Test task with http_request action
- [ ] Test task with python_code action
- [ ] Test task conditions (time_range, day_of_week)
- [ ] Test task error handling and retry
- [ ] Configure plugin settings in YAML
- [ ] Access plugin settings from plugin code
- [ ] Create and use a task template
- [ ] Define multiple environments
- [ ] Switch between environments
- [ ] Validate configuration file
- [ ] Test hot-reload by modifying config
- [ ] Test with invalid configuration
- [ ] Test completeness checking
- [ ] Test improvement suggestions

## Performance Testing

Test with:

- 100+ tasks
- 50+ plugins
- Large configuration files (>1000 lines)
- Rapid configuration changes (hot-reload stress test)
- Concurrent task execution

## Security Testing

Verify:

- Python code execution is sandboxed
- Environment variables are properly expanded
- Sensitive data is not logged
- Configuration validation prevents injection attacks
- File watching doesn't follow symlinks outside project

## Documentation Testing

Verify all examples in documentation work:

- [ ] All code examples in yaml-configuration-guide.md
- [ ] All code examples in enhanced-yaml-features.md
- [ ] All code examples in plugin-guide.md
- [ ] Example configuration in config.enhanced.example.yaml

## Notes

- Use pytest fixtures for common setup
- Mock external dependencies (HTTP requests, file system)
- Test both success and failure paths
- Test edge cases (empty lists, None values, invalid types)
- Test backward compatibility with old configurations
- Use parametrize for testing multiple similar cases
- Add docstrings to test functions
- Group related tests in classes

