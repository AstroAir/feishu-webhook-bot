# YAML Configuration Guide

This guide covers the advanced YAML configuration system for the Feishu Webhook Bot, including automated tasks, plugin configuration, environment management, and more.

## Table of Contents

- [Overview](#overview)
- [Basic Configuration](#basic-configuration)
- [Automated Tasks](#automated-tasks)
- [Task Templates](#task-templates)
- [Plugin Configuration](#plugin-configuration)
- [Environment Management](#environment-management)
- [Configuration Validation](#configuration-validation)
- [Hot-Reloading](#hot-reloading)
- [Best Practices](#best-practices)

## Overview

The advanced YAML configuration system provides:

- **Automated Tasks**: Define scheduled and event-driven tasks directly in YAML
- **Task Templates**: Create reusable task definitions
- **Plugin Configuration**: Configure plugin-specific settings
- **Environment Profiles**: Manage different configurations for dev/staging/production
- **Variable Substitution**: Use environment variables in configuration
- **Validation**: JSON schema validation for configuration files
- **Hot-Reload**: Reload configuration without restarting the bot

## Basic Configuration

### Minimal Configuration

```yaml
webhooks:
  - name: "default"
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL"

scheduler:
  enabled: true

plugins:
  enabled: true
  plugin_dir: "plugins"

logging:
  level: "INFO"
```

### Environment Variable Substitution

Use `${VAR_NAME}` syntax to reference environment variables:

```yaml
webhooks:
  - name: "default"
    url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_WEBHOOK_SECRET}"

# With default value
active_environment: "${ENVIRONMENT:development}"
```

## Automated Tasks

### Task Structure

```yaml
tasks:
  - name: "task_name"
    description: "Task description"
    enabled: true

    # Scheduling (choose one)
    schedule:
      mode: "interval"
      arguments:
        minutes: 5
    # OR
    cron: "0 9 * * *"  # Cron expression
    # OR
    interval:
      minutes: 5
      seconds: 30

    # Task dependencies
    depends_on: ["other_task"]
    run_after: ["prerequisite_task"]

    # Execution conditions
    conditions:
      - type: "time_range"
        start_time: "09:00"
        end_time: "18:00"
      - type: "day_of_week"
        days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
      - type: "environment"
        environment: "production"

    # Task actions
    actions:
      - type: "send_message"
        webhook: "default"
        message: "Hello, World!"

      - type: "plugin_method"
        plugin: "system-monitor"
        method: "check_health"
        save_as: "health_status"

      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/data"
          save_as: "api_response"

      - type: "python_code"
        code: |
          result = context.get('api_response')
          context['processed'] = process_data(result)

    # Error handling
    error_handling:
      on_failure: "notify"  # log, notify, disable, ignore
      retry_on_failure: true
      max_retries: 3
      retry_delay: 60
      notification_webhook: "alerts"

    # Execution settings
    timeout: 300
    priority: 100
    max_concurrent: 1

    # Task context
    context:
      custom_var: "value"
```

### Scheduling Options

#### Interval Scheduling

```yaml
schedule:
  mode: "interval"
  arguments:
    minutes: 5
    seconds: 30
```

#### Cron Scheduling

```yaml
cron: "0 9 * * *"  # Daily at 9 AM
```

Cron format: `minute hour day month day_of_week`

Examples:

- `"0 9 * * *"` - Daily at 9:00 AM
- `"*/15 * * * *"` - Every 15 minutes
- `"0 0 * * 0"` - Weekly on Sunday at midnight
- `"0 2 1 * *"` - Monthly on the 1st at 2:00 AM

### Task Actions

#### Send Message

```yaml
- type: "send_message"
  webhook: "default"
  message: "Simple text message"

# With template
- type: "send_message"
  webhook: "default"
  template: "alert"
  template_vars:
    title: "System Alert"
    severity: "high"
```

#### Plugin Method

```yaml
- type: "plugin_method"
  plugin: "system-monitor"
  method: "get_cpu_usage"
  args: [60]  # Positional arguments
  kwargs:     # Keyword arguments
    interval: 60
  save_as: "cpu_data"
```

#### HTTP Request

```yaml
- type: "http_request"
  request:
    method: "POST"
    url: "https://api.example.com/endpoint"
    headers:
      Authorization: "Bearer ${API_TOKEN}"
      Content-Type: "application/json"
    json:
      key: "value"
    timeout: 30
    save_as: "response"
```

#### Python Code

```yaml
- type: "python_code"
  code: |
    import datetime
    now = datetime.datetime.now()
    context['timestamp'] = now.isoformat()
    context['hour'] = now.hour
```

### Task Conditions

#### Time Range

```yaml
conditions:
  - type: "time_range"
    start_time: "09:00"
    end_time: "18:00"
```

#### Day of Week

```yaml
conditions:
  - type: "day_of_week"
    days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
```

#### Environment

```yaml
conditions:
  - type: "environment"
    environment: "production"
```

#### Custom Expression

```yaml
conditions:
  - type: "custom"
    expression: "context.get('value', 0) > 100"
```

## Task Templates

Define reusable task templates:

```yaml
task_templates:
  - name: "http_health_check"
    description: "Template for HTTP health checks"
    base_task:
      name: "template"
      schedule:
        mode: "interval"
        arguments:
          minutes: 5
      actions:
        - type: "http_request"
          request:
            method: "GET"
            url: "${url}"
            save_as: "response"
        - type: "send_message"
          webhook: "default"
          message: "Health check for ${service_name}: ${status}"
    parameters:
      - name: "url"
        type: "string"
        required: true
      - name: "service_name"
        type: "string"
        required: true
      - name: "status"
        type: "string"
        default: "OK"
```

Use templates in code:

```python
from feishu_webhook_bot.tasks import create_task_from_template_yaml

task = create_task_from_template_yaml(
    template_config,
    "api_health_check",
    {
        "url": "https://api.example.com/health",
        "service_name": "API Server",
        "status": "Healthy"
    }
)
```

## Plugin Configuration

Configure plugin-specific settings:

```yaml
plugins:
  enabled: true
  plugin_dir: "plugins"
  auto_reload: true

  plugin_settings:
    - plugin_name: "system-monitor"
      enabled: true
      priority: 10  # Lower numbers load first
      settings:
        cpu_threshold: 80
        memory_threshold: 85
        check_interval: 300

    - plugin_name: "daily-greeting"
      enabled: true
      priority: 50
      settings:
        morning_time: "09:00"
        custom_message: "Have a great day!"
```

Access in plugin code:

```python
class SystemMonitorPlugin(BasePlugin):
    def on_load(self):
        # Get specific setting
        threshold = self.get_config_value("cpu_threshold", 80)

        # Get all settings
        all_settings = self.get_all_config()
```

## Environment Management

Define environment-specific configurations:

```yaml
environments:
  - name: "development"
    description: "Development environment"
    variables:
      FEISHU_WEBHOOK_URL: "https://...dev-webhook"
      LOG_LEVEL: "DEBUG"
    overrides:
      logging:
        level: "DEBUG"
      plugins:
        auto_reload: true

  - name: "production"
    description: "Production environment"
    variables:
      FEISHU_WEBHOOK_URL: "https://...prod-webhook"
      LOG_LEVEL: "WARNING"
    overrides:
      logging:
        level: "WARNING"
      plugins:
        auto_reload: false

active_environment: "${ENVIRONMENT:development}"
```

Set environment via environment variable:

```bash
export ENVIRONMENT=production
python -m feishu_webhook_bot
```

## Configuration Validation

### Validate Configuration File

```python
from feishu_webhook_bot.core.validation import validate_yaml_config

is_valid, errors = validate_yaml_config("config.yaml")
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

### Generate JSON Schema

```python
from feishu_webhook_bot.core.validation import generate_json_schema

schema = generate_json_schema("config-schema.json")
```

### Check Configuration Completeness

```python
from feishu_webhook_bot.core.validation import check_config_completeness

info = check_config_completeness("config.yaml")
print(f"Completeness: {info['completeness_percentage']}%")
print(f"Missing sections: {info['missing_sections']}")
```

## Hot-Reloading

Enable configuration hot-reload:

```yaml
config_hot_reload: true
```

The bot will automatically reload configuration when the file changes.

Manual reload in code:

```python
from feishu_webhook_bot.core.config_watcher import create_config_watcher

bot = FeishuBot.from_yaml("config.yaml")
watcher = create_config_watcher("config.yaml", bot)
watcher.start()

# Later...
watcher.stop()
```

## Best Practices

1. **Use Environment Variables**: Store sensitive data in environment variables
2. **Validate Configuration**: Always validate before deploying
3. **Use Templates**: Create reusable task templates for common patterns
4. **Environment Profiles**: Maintain separate profiles for dev/staging/production
5. **Error Handling**: Configure appropriate error handling for each task
6. **Task Dependencies**: Use `depends_on` and `run_after` for task ordering
7. **Conditions**: Use conditions to control when tasks run
8. **Logging**: Configure appropriate log levels for each environment
9. **Hot-Reload**: Enable in development, disable in production
10. **Documentation**: Document custom tasks and templates

## Example: Complete Configuration

See `config.example.yaml` for a complete example with all features.
