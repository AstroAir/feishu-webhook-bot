# Advanced YAML Configuration Features

This document provides an overview of the advanced YAML configuration system for the Feishu Webhook Bot.

## What's New

The advanced YAML configuration system adds powerful new capabilities:

### 1. **Automated Tasks** 🤖

Define scheduled and event-driven tasks directly in YAML configuration:

```yaml
tasks:
  - name: "api_health_check"
    description: "Check API health every 5 minutes"
    enabled: true
    schedule:
      mode: "interval"
      arguments:
        minutes: 5
    actions:
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/health"
      - type: "send_message"
        webhook: "default"
        message: "API is healthy!"
```

### 2. **Task Templates** 📋

Create reusable task definitions:

```yaml
task_templates:
  - name: "http_health_check"
    description: "Template for HTTP health checks"
    base_task:
      schedule:
        mode: "interval"
        arguments:
          minutes: 5
      actions:
        - type: "http_request"
          request:
            url: "${url}"
        - type: "send_message"
          message: "Health check: ${status}"
    parameters:
      - name: "url"
        type: "string"
        required: true
```

### 3. **Plugin Configuration** 🔌

Configure plugin-specific settings in YAML:

```yaml
plugins:
  plugin_settings:
    - plugin_name: "system-monitor"
      enabled: true
      priority: 10
      settings:
        cpu_threshold: 80
        memory_threshold: 85
```

### 4. **Environment Profiles** 🌍

Manage different configurations for dev/staging/production:

```yaml
environments:
  - name: "development"
    variables:
      FEISHU_WEBHOOK_URL: "https://...dev-webhook"
    overrides:
      logging:
        level: "DEBUG"

  - name: "production"
    variables:
      FEISHU_WEBHOOK_URL: "https://...prod-webhook"
    overrides:
      logging:
        level: "WARNING"

active_environment: "${ENVIRONMENT:development}"
```

### 5. **Configuration Validation** ✅

Validate configuration files before deployment:

```python
from feishu_webhook_bot.core.validation import validate_yaml_config

is_valid, errors = validate_yaml_config("config.yaml")
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

### 6. **Hot-Reload** 🔥

Reload configuration without restarting:

```yaml
config_hot_reload: true
```

## Quick Start

### 1. Use the Example Configuration

Copy the example configuration:

```bash
cp config.example.yaml config.yaml
```

Edit the configuration to add your webhook URLs and customize settings.

### 2. Define Your First Task

Add a simple task to your configuration:

```yaml
tasks:
  - name: "daily_greeting"
    description: "Send a greeting every morning"
    enabled: true
    cron: "0 9 * * *"  # Daily at 9 AM
    actions:
      - type: "send_message"
        webhook: "default"
        message: "Good morning! Have a great day! 🌅"
```

### 3. Configure Your Plugins

Add plugin-specific settings:

```yaml
plugins:
  enabled: true
  plugin_dir: "plugins"
  plugin_settings:
    - plugin_name: "system-monitor"
      enabled: true
      settings:
        cpu_threshold: 80
        check_interval: 300
```

### 4. Set Up Environment Profiles

Define environment-specific configurations:

```yaml
environments:
  - name: "development"
    variables:
      LOG_LEVEL: "DEBUG"
    overrides:
      logging:
        level: "DEBUG"

active_environment: "${ENVIRONMENT:development}"
```

### 5. Start the Bot

```bash
python -m feishu_webhook_bot
```

## Key Features

### Task Scheduling

Tasks support multiple scheduling options:

- **Interval**: Run every N minutes/hours/days
- **Cron**: Use cron expressions for complex schedules
- **Dependencies**: Define task execution order

### Task Actions

Tasks can perform various actions:

- **send_message**: Send messages to Feishu
- **plugin_method**: Call plugin methods
- **http_request**: Make HTTP requests
- **python_code**: Execute Python code

### Task Conditions

Control when tasks run:

- **time_range**: Only run during specific hours
- **day_of_week**: Only run on specific days
- **environment**: Only run in specific environments
- **custom**: Use Python expressions

### Error Handling

Configure how tasks handle failures:

- **on_failure**: log, notify, disable, or ignore
- **retry_on_failure**: Automatically retry failed tasks
- **max_retries**: Maximum number of retry attempts
- **retry_delay**: Delay between retries

## Documentation

For detailed documentation, see:

- **[YAML Configuration Guide](yaml-configuration-guide.md)** - Complete reference for all configuration options
- **[Plugin Guide](plugin-guide.md)** - Updated with new plugin configuration features
- **[Getting Started](../getting-started/first-steps.md)** - Basic setup and usage

## Examples

### Example 1: API Health Check

```yaml
tasks:
  - name: "api_health_check"
    enabled: true
    schedule:
      mode: "interval"
      arguments:
        minutes: 5
    conditions:
      - type: "environment"
        environment: "production"
    actions:
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/health"
          timeout: 10
          save_as: "health_response"
      - type: "send_message"
        webhook: "default"
        message: "API Health: ${health_response.status}"
    error_handling:
      on_failure: "notify"
      retry_on_failure: true
      max_retries: 3
```

### Example 2: Daily Report

```yaml
tasks:
  - name: "daily_report"
    enabled: true
    cron: "0 9 * * *"  # Daily at 9 AM
    conditions:
      - type: "day_of_week"
        days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
    actions:
      - type: "plugin_method"
        plugin: "system-monitor"
        method: "get_system_stats"
        save_as: "stats"
      - type: "send_message"
        webhook: "default"
        template: "daily_report"
        template_vars:
          stats: "${stats}"
```

### Example 3: Cleanup Task

```yaml
tasks:
  - name: "cleanup_old_logs"
    enabled: true
    cron: "0 3 * * 0"  # Weekly on Sunday at 3 AM
    actions:
      - type: "python_code"
        code: |
          import os
          from pathlib import Path
          import time

          log_dir = Path("logs")
          cutoff_time = time.time() - (30 * 24 * 60 * 60)
          deleted_count = 0

          for log_file in log_dir.glob("*.log*"):
              if log_file.stat().st_mtime < cutoff_time:
                  log_file.unlink()
                  deleted_count += 1

          context["deleted_count"] = deleted_count
      - type: "send_message"
        webhook: "default"
        message: "Cleaned up ${deleted_count} old log files"
```

## Migration Guide

### From Old Configuration

If you have an existing configuration, you can continue using it. The new features are backward compatible.

To use the new features:

1. Add `tasks` section for automated tasks
2. Add `plugin_settings` under `plugins` for plugin configuration
3. Add `environments` section for environment profiles
4. Set `config_hot_reload: true` to enable hot-reload

### Validation

Before deploying, validate your configuration:

```python
from feishu_webhook_bot.core.validation import (
    validate_yaml_config,
    check_config_completeness,
    suggest_config_improvements
)

# Validate
is_valid, errors = validate_yaml_config("config.yaml")

# Check completeness
info = check_config_completeness("config.yaml")
print(f"Completeness: {info['completeness_percentage']}%")

# Get suggestions
suggestions = suggest_config_improvements("config.yaml")
for suggestion in suggestions:
    print(f"💡 {suggestion}")
```

## Best Practices

1. **Use Environment Variables**: Store sensitive data in environment variables
2. **Validate Before Deploy**: Always validate configuration before deploying
3. **Use Templates**: Create reusable task templates for common patterns
4. **Environment Profiles**: Maintain separate profiles for dev/staging/production
5. **Error Handling**: Configure appropriate error handling for each task
6. **Task Dependencies**: Use `depends_on` and `run_after` for task ordering
7. **Conditions**: Use conditions to control when tasks run
8. **Logging**: Configure appropriate log levels for each environment
9. **Hot-Reload**: Enable in development, disable in production
10. **Documentation**: Document custom tasks and templates

## Troubleshooting

### Configuration Not Loading

Check for YAML syntax errors:

```python
from feishu_webhook_bot.core.validation import validate_yaml_config

is_valid, errors = validate_yaml_config("config.yaml")
if not is_valid:
    for error in errors:
        print(error)
```

### Tasks Not Running

1. Check if scheduler is enabled: `scheduler.enabled: true`
2. Check if task is enabled: `tasks[].enabled: true`
3. Check task conditions
4. Check logs for errors

### Plugin Settings Not Working

1. Ensure plugin name matches exactly
2. Check plugin is enabled
3. Verify settings are accessed correctly in plugin code

### Hot-Reload Not Working

1. Ensure `config_hot_reload: true`
2. Check file permissions
3. Verify config file path is correct

## Support

For issues or questions:

- Check the [documentation](yaml-configuration-guide.md)
- Review the example configuration files in the repository
- Open an issue on GitHub
