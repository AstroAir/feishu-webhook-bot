# Task System Guide

This guide explains how to use the advanced task execution system in the Feishu Webhook Bot framework.

## Table of Contents

- [Overview](#overview)
- [Task Definition](#task-definition)
- [Task Actions](#task-actions)
- [Task Conditions](#task-conditions)
- [Task Dependencies](#task-dependencies)
- [Task Templates](#task-templates)
- [Error Handling](#error-handling)
- [AI Integration](#ai-integration)
- [TaskManager API](#taskmanager-api)
- [Best Practices](#best-practices)

## Overview

The task system provides advanced task execution capabilities beyond simple automation:

- **Multi-Action Tasks**: Execute multiple actions in sequence
- **Conditional Execution**: Run tasks only when conditions are met
- **Task Dependencies**: Define execution order between tasks
- **Task Templates**: Create reusable task definitions
- **Error Handling**: Configurable retry and failure handling
- **AI Integration**: Execute AI-powered actions within tasks

### Task vs Automation

| Feature | Automation | Task |
|---------|------------|------|
| Complexity | Simple workflows | Complex multi-step workflows |
| Actions | send_text, send_template, http_request | All automation actions + plugin_method, python_code, ai_chat, ai_query |
| Dependencies | None | Task dependencies and ordering |
| Conditions | Event conditions only | Time range, day of week, environment, custom |
| Templates | Message templates | Task templates |
| Error Handling | Basic | Advanced with retry, notifications |

## Task Definition

### Basic Structure

```yaml
tasks:
  - name: "daily-report"
    description: "Generate and send daily report"
    enabled: true
    
    # Scheduling (required - choose one)
    schedule:
      mode: "cron"
      arguments:
        hour: "18"
        minute: "0"
    
    # Actions to execute (required)
    actions:
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/stats"
          save_as: "stats"
      
      - type: "send_message"
        message: "Daily stats: ${stats.total}"
        webhooks: ["default"]
    
    # Optional settings
    timeout: 300
    priority: 100
    max_concurrent: 1
    context:
      report_type: "daily"
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | Required | Unique task identifier |
| `description` | string | None | Human-readable description |
| `enabled` | bool | true | Whether task is active |
| `schedule` | object | Required* | Schedule configuration |
| `cron` | string | Required* | Cron expression |
| `interval` | object | Required* | Interval configuration |
| `actions` | list | Required | Actions to execute |
| `conditions` | list | [] | Execution conditions |
| `depends_on` | list | [] | Task dependencies |
| `run_after` | list | [] | Tasks that must complete first |
| `parameters` | list | [] | Task parameters |
| `error_handling` | object | Default | Error handling configuration |
| `timeout` | float | None | Task timeout in seconds |
| `priority` | int | 100 | Execution priority (lower = higher) |
| `max_concurrent` | int | 1 | Max concurrent executions |
| `context` | dict | {} | Additional context variables |

*One of `schedule`, `cron`, or `interval` is required.

## Task Actions

### Send Message

Send a message to webhooks:

```yaml
actions:
  - type: "send_message"
    message: "Hello, World!"
    webhooks: ["default", "alerts"]
  
  # With template
  - type: "send_message"
    template: "daily_report"
    parameters:
      date: "${event_date}"
      status: "operational"
    webhooks: ["default"]
```

### HTTP Request

Make HTTP requests and save responses:

```yaml
actions:
  - type: "http_request"
    request:
      method: "POST"
      url: "https://api.example.com/data"
      headers:
        Authorization: "Bearer ${API_TOKEN}"
        Content-Type: "application/json"
      json_body:
        query: "status"
      timeout: 30
      save_as: "api_response"
```

### Plugin Method

Call a plugin method:

```yaml
actions:
  - type: "plugin_method"
    plugin_name: "system-monitor"
    method_name: "get_cpu_usage"
    parameters:
      interval: 60
```

### Python Code

Execute Python code:

```yaml
actions:
  - type: "python_code"
    code: |
      import datetime
      now = datetime.datetime.now()
      context['timestamp'] = now.isoformat()
      
      # Access previous action results
      stats = context.get('api_response', {})
      context['processed'] = stats.get('count', 0) * 2
```

### AI Chat

Conversational AI with context:

```yaml
actions:
  - type: "ai_chat"
    ai_prompt: "Analyze this data and provide insights: ${api_response}"
    ai_user_id: "task_analyst"
    ai_temperature: 0.7
    ai_save_response_as: "analysis"
```

### AI Query

One-off AI query without conversation history:

```yaml
actions:
  - type: "ai_query"
    ai_prompt: "Summarize: ${data}"
    ai_system_prompt: "You are a data analyst."
    ai_max_tokens: 500
    ai_save_response_as: "summary"
```

## Task Conditions

### Time Range

Execute only within a time range:

```yaml
conditions:
  - type: "time_range"
    start_time: "09:00"
    end_time: "18:00"
```

### Day of Week

Execute only on specific days:

```yaml
conditions:
  - type: "day_of_week"
    days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
```

### Environment

Execute only in specific environment:

```yaml
conditions:
  - type: "environment"
    environment: "production"
```

### Custom Expression

Execute based on custom Python expression:

```yaml
conditions:
  - type: "custom"
    expression: "context.get('value', 0) > 100"
```

### Multiple Conditions

All conditions must be met (AND logic):

```yaml
conditions:
  - type: "time_range"
    start_time: "09:00"
    end_time: "18:00"
  - type: "day_of_week"
    days: ["monday", "wednesday", "friday"]
  - type: "environment"
    environment: "production"
```

## Task Dependencies

### depends_on

Tasks that must exist (not necessarily completed):

```yaml
tasks:
  - name: "process-data"
    depends_on: ["fetch-data"]
    # ...
```

### run_after

Tasks that must complete before this task runs:

```yaml
tasks:
  - name: "fetch-data"
    schedule:
      mode: "cron"
      arguments: { hour: "8", minute: "0" }
    actions:
      - type: "http_request"
        request:
          url: "https://api.example.com/data"
          save_as: "raw_data"

  - name: "process-data"
    run_after: ["fetch-data"]
    schedule:
      mode: "cron"
      arguments: { hour: "8", minute: "30" }
    actions:
      - type: "python_code"
        code: |
          # Process the fetched data
          raw = context.get('raw_data', {})
          context['processed'] = transform(raw)

  - name: "send-report"
    run_after: ["process-data"]
    schedule:
      mode: "cron"
      arguments: { hour: "9", minute: "0" }
    actions:
      - type: "send_message"
        message: "Report: ${processed}"
```

## Task Templates

### Defining Templates

```yaml
task_templates:
  - name: "health_check"
    description: "Template for health check tasks"
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
            url: "${endpoint_url}"
            save_as: "health"
        - type: "send_message"
          message: "${service_name} health: ${health.status}"
          webhooks: ["${webhook}"]
      error_handling:
        on_failure: "notify"
        notification_webhook: "alerts"
    parameters:
      - name: "endpoint_url"
        type: "string"
        required: true
        description: "Health check endpoint URL"
      - name: "service_name"
        type: "string"
        required: true
        description: "Service name for notifications"
      - name: "webhook"
        type: "string"
        default: "default"
        description: "Target webhook"
```

### Using Templates

```python
from feishu_webhook_bot.tasks import create_task_from_template_yaml

# Create task from template
task = create_task_from_template_yaml(
    template_config,
    task_name="api-health-check",
    parameters={
        "endpoint_url": "https://api.example.com/health",
        "service_name": "API Server",
        "webhook": "monitoring",
    }
)
```

## Error Handling

### Configuration

```yaml
error_handling:
  retry_on_failure: true
  max_retries: 3
  retry_delay: 60.0  # seconds
  on_failure_action: "notify"  # log, notify, disable, ignore
  notification_webhook: "alerts"
```

### Failure Actions

| Action | Description |
|--------|-------------|
| `log` | Log the error (default) |
| `notify` | Send notification to webhook |
| `disable` | Disable the task after failure |
| `ignore` | Ignore the error and continue |

### Example with Notification

```yaml
tasks:
  - name: "critical-task"
    error_handling:
      retry_on_failure: true
      max_retries: 5
      retry_delay: 30.0
      on_failure_action: "notify"
      notification_webhook: "alerts"
    actions:
      - type: "http_request"
        request:
          url: "https://critical-api.example.com/process"
          save_as: "result"
```

## AI Integration

### AI-Powered Task Example

```yaml
tasks:
  - name: "ai-analysis"
    description: "AI-powered data analysis"
    schedule:
      mode: "cron"
      arguments: { hour: "9", minute: "0" }
    actions:
      # Step 1: Fetch data
      - type: "http_request"
        request:
          url: "https://api.example.com/metrics"
          save_as: "metrics"
      
      # Step 2: AI analysis
      - type: "ai_query"
        ai_prompt: |
          Analyze these metrics and identify trends:
          ${metrics}
          
          Provide:
          1. Key insights
          2. Anomalies detected
          3. Recommendations
        ai_temperature: 0.3
        ai_save_response_as: "analysis"
      
      # Step 3: Send report
      - type: "send_message"
        template: "analysis_report"
        parameters:
          date: "${event_date}"
          analysis: "${analysis}"
        webhooks: ["default"]
```

### Multi-Step AI Workflow

```yaml
tasks:
  - name: "research-and-report"
    actions:
      # Research phase
      - type: "ai_query"
        ai_prompt: "Research latest trends in ${topic}"
        ai_user_id: "researcher"
        ai_save_response_as: "research"
      
      # Analysis phase
      - type: "ai_query"
        ai_prompt: |
          Based on this research: ${research}
          Provide detailed analysis with:
          - Opportunities
          - Challenges
          - Recommendations
        ai_user_id: "analyst"
        ai_save_response_as: "analysis"
      
      # Summary phase
      - type: "ai_query"
        ai_prompt: |
          Create executive summary from:
          Research: ${research}
          Analysis: ${analysis}
        ai_user_id: "summarizer"
        ai_max_tokens: 300
        ai_save_response_as: "summary"
      
      # Send report
      - type: "send_message"
        message: |
          📊 Research Report: ${topic}
          
          ${summary}
        webhooks: ["default"]
    context:
      topic: "AI in enterprise"
```

## TaskManager API

### Python Usage

```python
from feishu_webhook_bot.tasks import TaskManager, TaskExecutor

# Create manager
manager = TaskManager(
    config=bot_config,
    scheduler=scheduler,
    clients=clients,
    ai_agent=ai_agent,  # Optional
)

# Start manager
await manager.start()

# Get task status
status = manager.get_task_status("daily-report")
print(f"Status: {status['state']}")
print(f"Last run: {status['last_run']}")
print(f"Next run: {status['next_run']}")

# Manually trigger task
await manager.trigger_task("daily-report")

# Pause task
manager.pause_task("daily-report")

# Resume task
manager.resume_task("daily-report")

# Get all tasks
all_tasks = manager.list_tasks()

# Stop manager
await manager.stop()
```

### TaskExecutor

```python
from feishu_webhook_bot.tasks import TaskExecutor

executor = TaskExecutor(
    clients=clients,
    ai_agent=ai_agent,
)

# Execute task manually
result = await executor.execute(task_config, context={
    "custom_var": "value",
})

if result.success:
    print(f"Task completed: {result.outputs}")
else:
    print(f"Task failed: {result.error}")
```

## Best Practices

### 1. Use Meaningful Names

```yaml
tasks:
  - name: "daily-sales-report"  # Good
  - name: "task1"  # Bad
```

### 2. Set Appropriate Timeouts

```yaml
tasks:
  - name: "quick-check"
    timeout: 30  # Short timeout for quick tasks
  
  - name: "data-processing"
    timeout: 600  # Longer timeout for heavy processing
```

### 3. Configure Error Handling

```yaml
error_handling:
  retry_on_failure: true
  max_retries: 3
  retry_delay: 60.0
  on_failure_action: "notify"
```

### 4. Use Templates for Common Patterns

```yaml
task_templates:
  - name: "api_health_check"
    # Define once, use many times
```

### 5. Leverage Task Dependencies

```yaml
tasks:
  - name: "fetch"
    # ...
  - name: "process"
    run_after: ["fetch"]
  - name: "report"
    run_after: ["process"]
```

### 6. Use Conditions Wisely

```yaml
conditions:
  - type: "time_range"
    start_time: "09:00"
    end_time: "18:00"
  - type: "environment"
    environment: "production"
```

### 7. Monitor Task Execution

```python
# Check task status regularly
status = manager.get_task_status("critical-task")
if status['consecutive_failures'] > 3:
    alert("Task failing repeatedly!")
```

## Troubleshooting

### Task Not Running

1. Check if task is enabled
2. Verify schedule configuration
3. Check conditions are met
4. Review dependencies

### Action Failures

1. Check action configuration
2. Verify API endpoints
3. Review error logs
4. Test actions individually

### AI Actions Not Working

1. Verify AI is enabled in config
2. Check API key is set
3. Review AI agent logs
4. Test AI separately

## See Also

- [Automation Guide](automation-guide.md) - Simple declarative workflows
- [Scheduler Guide](scheduler-guide.md) - Job scheduling
- [AI Multi-Provider Guide](../ai/multi-provider.md) - AI configuration
- [YAML Configuration](yaml-configuration-guide.md) - Configuration reference
