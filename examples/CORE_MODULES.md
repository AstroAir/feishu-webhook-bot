# Core Module Examples

This directory contains comprehensive examples demonstrating all core modules of the Feishu Webhook Bot.

## Overview

The Feishu Webhook Bot is built on several core modules that work together to provide a powerful, extensible platform:

1. **Plugin System** - Extend bot functionality without modifying core code
2. **Task Scheduler** - Schedule periodic jobs with cron or interval triggers
3. **Automation Engine** - Define declarative workflows with various action types
4. **Task Manager** - Manage automated tasks with dependencies and retry logic
5. **Event Server** - Receive and process incoming Feishu webhook events

## Example Files

### 1. Plugin System (`plugin_demo.py`)

**Purpose**: Demonstrates the complete plugin system lifecycle and capabilities.

**Key Features**:

- Creating custom plugins by extending `BasePlugin`
- Plugin lifecycle hooks: `on_load()`, `on_enable()`, `on_disable()`, `on_unload()`
- Registering scheduled jobs from plugins
- Accessing bot resources (client, config, scheduler)
- Plugin-specific configuration
- Event handling in plugins
- Hot-reload functionality
- Plugin loading priority

**Quick Start**:

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="My custom plugin"
        )

    def on_enable(self):
        # Register a scheduled job
        self.register_job(
            self.my_task,
            trigger="interval",
            minutes=5
        )

    def my_task(self):
        self.client.send_text("Hello from plugin!")
```

**Run the demo**:

```bash
python examples/plugin_demo.py
```

### 2. Task Scheduler (`scheduler_demo.py`)

**Purpose**: Demonstrates comprehensive task scheduling capabilities.

**Key Features**:

- Interval-based scheduling (every N seconds/minutes/hours)
- Cron-based scheduling (specific times/days)
- Job management (add, remove, pause, resume)
- Persistent job store (SQLite) vs in-memory
- Timezone-aware scheduling
- Job decorators (`@job`)
- Error handling and retry logic

**Quick Start**:

```python
from feishu_webhook_bot.scheduler import TaskScheduler, job
from feishu_webhook_bot.core.config import SchedulerConfig

# Create scheduler
config = SchedulerConfig(enabled=True, timezone="UTC")
scheduler = TaskScheduler(config)
scheduler.start()

# Add interval job
scheduler.add_job(
    my_function,
    trigger="interval",
    minutes=10
)

# Add cron job
scheduler.add_job(
    my_function,
    trigger="cron",
    hour="9",
    minute="0"
)

# Or use decorator
@job(trigger="interval", minutes=5)
def periodic_task():
    print("Running every 5 minutes")

scheduler.register_job(periodic_task)
```

**Run the demo**:

```bash
python examples/scheduler_demo.py
```

### 3. Automation Engine (`automation_demo.py`)

**Purpose**: Demonstrates declarative workflow automation.

**Key Features**:

- Declarative workflow definitions in YAML/config
- Schedule-based triggers
- Event-based triggers
- Multiple action types:
  - Send messages (text, rich text, cards)
  - HTTP requests (GET, POST, etc.)
  - Python code execution
  - Plugin method calls
- Template rendering with variable substitution
- Conditional execution

**Quick Start**:

```python
from feishu_webhook_bot.core.config import (
    AutomationRule,
    AutomationTriggerConfig,
    AutomationActionConfig,
    ScheduleConfig
)

# Define automation rule
rule = AutomationRule(
    name="daily-report",
    enabled=True,
    trigger=AutomationTriggerConfig(
        type="schedule",
        schedule=ScheduleConfig(
            mode="cron",
            arguments={"hour": "9", "minute": "0"}
        )
    ),
    actions=[
        AutomationActionConfig(
            type="send_text",
            webhook="default",
            text="Good morning! Daily report ready."
        ),
        AutomationActionConfig(
            type="http_request",
            http_request={
                "url": "https://api.example.com/report",
                "method": "GET"
            }
        )
    ]
)
```

**Run the demo**:

```bash
python examples/automation_demo.py
```

### 4. Task Manager (`task_manager_demo.py`)

**Purpose**: Demonstrates automated task execution and management.

**Key Features**:

- Automated task execution
- Task dependencies (task A must complete before task B)
- Retry logic with configurable attempts and delays
- Task conditions (environment, time, day)
- Integration with plugins
- Cron and interval scheduling
- Multiple actions per task

**Quick Start**:

```python
from feishu_webhook_bot.core.config import (
    TaskDefinitionConfig,
    TaskActionConfig
)

# Define task
task = TaskDefinitionConfig(
    name="backup-task",
    enabled=True,
    description="Daily backup task",
    cron="0 2 * * *",  # 2 AM daily
    retry_on_failure=True,
    max_retries=3,
    retry_delay=60,
    actions=[
        TaskActionConfig(
            type="plugin_method",
            plugin="backup-plugin",
            method="perform_backup"
        ),
        TaskActionConfig(
            type="send_message",
            webhook="default",
            message="Backup completed successfully"
        )
    ]
)
```

**Run the demo**:

```bash
python examples/task_manager_demo.py
```

### 5. Event Server (`event_server_demo.py`)

**Purpose**: Demonstrates receiving and processing Feishu webhook events.

**Key Features**:

- FastAPI-based HTTP server
- Token verification for security
- HMAC signature validation
- URL verification challenge handling
- Event dispatching to plugins
- Health check endpoint
- Concurrent event handling

**Quick Start**:

```python
from feishu_webhook_bot.core.config import EventServerConfig

# Configure event server
config = EventServerConfig(
    enabled=True,
    host="0.0.0.0",
    port=8080,
    path="/webhook",
    verification_token="your-token",
    signature_secret="your-secret"
)

# Create bot with event server
bot = FeishuBot(config)

# Events are automatically dispatched to plugins
class EventHandlerPlugin(BasePlugin):
    def handle_event(self, event, context=None):
        event_type = event.get("type")
        if event_type == "message":
            content = event.get("message", {}).get("content", "")
            self.client.send_text(f"Echo: {content}")
```

**Run the demo**:

```bash
python examples/event_server_demo.py
```

**Test with curl**:

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"message","message":{"content":"Hello!"}}'
```

## Integration Patterns

### Pattern 1: Plugin + Scheduler

Plugins can register scheduled jobs for periodic tasks:

```python
class MonitoringPlugin(BasePlugin):
    def on_enable(self):
        # Check system health every 5 minutes
        self.register_job(
            self.check_health,
            trigger="interval",
            minutes=5
        )

    def check_health(self):
        # Perform health check
        status = self.get_system_status()
        if status["cpu"] > 80:
            self.client.send_text("⚠️ High CPU usage!")
```

### Pattern 2: Automation + Plugin

Automation rules can call plugin methods:

```python
# In config.yaml
automations:
  - name: process-data
    trigger:
      type: schedule
      schedule:
        mode: cron
        arguments: {hour: "*/6"}  # Every 6 hours
    actions:
      - type: plugin_method
        plugin: data-processor
        method: process_batch
```

### Pattern 3: Event Server + Plugin

Plugins handle incoming events from the event server:

```python
class ChatbotPlugin(BasePlugin):
    def handle_event(self, event, context=None):
        if event.get("type") == "message":
            message = event.get("message", {})
            user_text = message.get("content", "")

            # Process message and respond
            response = self.generate_response(user_text)
            self.client.send_text(response)
```

### Pattern 4: Task Manager + Dependencies

Tasks can depend on other tasks:

```python
tasks = [
    TaskDefinitionConfig(
        name="fetch-data",
        schedule={"mode": "cron", "arguments": {"hour": "1"}},
        actions=[...]
    ),
    TaskDefinitionConfig(
        name="process-data",
        depends_on=["fetch-data"],  # Runs after fetch-data
        schedule={"mode": "cron", "arguments": {"hour": "1"}},
        actions=[...]
    ),
    TaskDefinitionConfig(
        name="send-report",
        depends_on=["process-data"],  # Runs after process-data
        schedule={"mode": "cron", "arguments": {"hour": "1"}},
        actions=[...]
    )
]
```

## Best Practices

### Plugin Development

1. **Keep plugins focused** - Each plugin should have a single, clear purpose
2. **Use configuration** - Make plugins configurable via `plugin_settings`
3. **Handle errors gracefully** - Use try-except blocks and log errors
4. **Clean up resources** - Implement `on_disable()` to clean up
5. **Test hot-reload** - Ensure plugins can be reloaded without issues

### Scheduling

1. **Use cron for specific times** - e.g., "9 AM every weekday"
2. **Use intervals for periodic tasks** - e.g., "every 5 minutes"
3. **Set appropriate timezones** - Use timezone-aware scheduling
4. **Persist important jobs** - Use SQLite job store for critical tasks
5. **Handle job failures** - Implement error handling in job functions

### Automation

1. **Start simple** - Begin with basic rules and add complexity gradually
2. **Use templates** - Define reusable message templates
3. **Test conditions** - Verify conditions work as expected
4. **Chain actions carefully** - Consider failure scenarios
5. **Monitor execution** - Check logs for automation results

### Task Management

1. **Define clear dependencies** - Document task relationships
2. **Set reasonable retries** - Don't retry indefinitely
3. **Use conditions wisely** - Prevent unnecessary task execution
4. **Test in isolation** - Test each task independently first
5. **Monitor task status** - Track execution counts and failures

### Event Handling

1. **Validate events** - Always verify event structure
2. **Use token verification** - Enable security features in production
3. **Handle all event types** - Implement handlers for expected events
4. **Respond quickly** - Keep event handlers fast
5. **Log events** - Track all incoming events for debugging

## Troubleshooting

See the main [README.md](README.md#troubleshooting) for detailed troubleshooting guides.

## Additional Resources

- [Main README](../README.md)
- [Authentication Examples](AUTH_EXAMPLES.md)
- [AI Features Documentation](../ADVANCED_AI_FEATURES.md)
- [MCP Integration Guide](../docs/MCP_INTEGRATION.md)
- [API Documentation](../docs/)
