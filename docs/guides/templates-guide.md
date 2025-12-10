# Templates Guide

Complete guide to the message template system in Feishu Webhook Bot.

## Table of Contents

- [Overview](#overview)
- [Template Types](#template-types)
- [Defining Templates](#defining-templates)
- [Using Templates](#using-templates)
- [Template Variables](#template-variables)
- [Conditional Content](#conditional-content)
- [Template Inheritance](#template-inheritance)
- [Dynamic Templates](#dynamic-templates)
- [Best Practices](#best-practices)

## Overview

The template system allows you to define reusable message formats that can be populated with dynamic data at runtime.

### Benefits

- **Consistency** - Standardized message formats across your application
- **Maintainability** - Update templates in one place
- **Separation** - Keep message content separate from code
- **Reusability** - Use the same template with different data

## Template Types

### Text Templates

Simple text with variable substitution:

```yaml
templates:
  greeting:
    type: text
    content: "Hello, {name}! Welcome to {team}."
```

### Markdown Templates

Formatted text templates:

```yaml
templates:
  status_update:
    type: markdown
    content: |
      ## Status Update
      
      **Service:** {service}
      **Status:** {status}
      **Time:** {timestamp}
```

### Card Templates

Interactive card templates:

```yaml
templates:
  alert:
    type: card
    header:
      title: "{icon} {level}: {title}"
      template: "{color}"
    elements:
      - type: markdown
        content: "{message}"
      - type: divider
      - type: fields
        fields:
          - title: "Time"
            value: "{timestamp}"
          - title: "Source"
            value: "{source}"
      - type: actions
        actions:
          - type: button
            text: "View Details"
            url: "{details_url}"
```

### Rich Text Templates

Complex formatted text:

```yaml
templates:
  announcement:
    type: rich_text
    title: "{title}"
    content:
      - type: text
        text: "{intro}"
        bold: true
      - type: newline
      - type: text
        text: "{body}"
      - type: newline
      - type: link
        text: "Learn more"
        url: "{link_url}"
```

## Defining Templates

### In Configuration File

```yaml
# config.yaml
templates:
  # Simple text template
  welcome:
    type: text
    content: "Welcome, {username}!"
  
  # Markdown template
  report:
    type: markdown
    content: |
      # {title}
      
      **Date:** {date}
      **Author:** {author}
      
      {content}
  
  # Card template
  notification:
    type: card
    header:
      title: "{title}"
      template: blue
    elements:
      - type: markdown
        content: "{body}"
```

### Programmatically

```python
from feishu_webhook_bot.core.templates import TemplateRegistry, Template

registry = TemplateRegistry()

# Register text template
registry.register(Template(
    name="greeting",
    type="text",
    content="Hello, {name}!"
))

# Register card template
registry.register(Template(
    name="alert",
    type="card",
    header={"title": "{title}", "template": "red"},
    elements=[
        {"type": "markdown", "content": "{message}"}
    ]
))
```

### From External Files

```yaml
# config.yaml
templates:
  _include:
    - templates/alerts.yaml
    - templates/reports.yaml
```

```yaml
# templates/alerts.yaml
critical_alert:
  type: card
  header:
    title: "🚨 Critical Alert"
    template: red
  elements:
    - type: markdown
      content: "{message}"

warning_alert:
  type: card
  header:
    title: "⚠️ Warning"
    template: yellow
  elements:
    - type: markdown
      content: "{message}"
```

## Using Templates

### Basic Usage

```python
from feishu_webhook_bot import FeishuBot

bot = FeishuBot.from_config("config.yaml")

# Send using template
bot.send_template("greeting", name="John")

# Send with multiple variables
bot.send_template("report",
    title="Weekly Report",
    date="2025-01-15",
    author="System",
    content="All systems operational."
)
```

### With Webhook Selection

```python
# Send to specific webhook
bot.send_template("alert",
    webhook="alerts",
    level="WARNING",
    title="High CPU",
    message="CPU usage at 85%"
)

# Send to multiple webhooks
bot.send_template("announcement",
    webhooks=["general", "engineering"],
    title="Maintenance Notice",
    body="Scheduled maintenance tonight."
)
```

### Template Rendering Only

```python
# Render without sending
rendered = bot.render_template("greeting", name="John")
print(rendered)  # "Hello, John!"

# Render card to dict
card_dict = bot.render_template("alert",
    level="ERROR",
    title="Database Error",
    message="Connection failed"
)
```

## Template Variables

### Basic Variables

```yaml
templates:
  example:
    type: text
    content: "Hello, {name}! Your score is {score}."
```

```python
bot.send_template("example", name="Alice", score=95)
# Output: "Hello, Alice! Your score is 95."
```

### Default Values

```yaml
templates:
  greeting:
    type: text
    content: "Hello, {name:Guest}!"
    defaults:
      name: "Guest"
```

```python
bot.send_template("greeting")  # "Hello, Guest!"
bot.send_template("greeting", name="Bob")  # "Hello, Bob!"
```

### Nested Variables

```yaml
templates:
  user_info:
    type: markdown
    content: |
      **Name:** {user.name}
      **Email:** {user.email}
      **Role:** {user.role}
```

```python
user = {"name": "Alice", "email": "alice@example.com", "role": "Admin"}
bot.send_template("user_info", user=user)
```

### List Variables

```yaml
templates:
  task_list:
    type: markdown
    content: |
      ## Tasks
      
      {tasks_formatted}
```

```python
tasks = ["Task 1", "Task 2", "Task 3"]
tasks_formatted = "\n".join(f"- {t}" for t in tasks)
bot.send_template("task_list", tasks_formatted=tasks_formatted)
```

### Date/Time Formatting

```python
from datetime import datetime

bot.send_template("report",
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
```

## Conditional Content

### Using Python Logic

```python
def get_status_template(status: str) -> str:
    if status == "critical":
        return "critical_alert"
    elif status == "warning":
        return "warning_alert"
    else:
        return "info_alert"

bot.send_template(get_status_template(status), message=message)
```

### Template Selection

```yaml
templates:
  alert_critical:
    type: card
    header:
      title: "🚨 Critical"
      template: red
    elements:
      - type: markdown
        content: "{message}"

  alert_warning:
    type: card
    header:
      title: "⚠️ Warning"
      template: yellow
    elements:
      - type: markdown
        content: "{message}"

  alert_info:
    type: card
    header:
      title: "ℹ️ Info"
      template: blue
    elements:
      - type: markdown
        content: "{message}"
```

```python
def send_alert(level: str, message: str):
    template_name = f"alert_{level}"
    bot.send_template(template_name, message=message)
```

### Dynamic Elements

```python
from feishu_webhook_bot.core.client import CardBuilder

def build_alert_card(level: str, message: str, show_actions: bool = True):
    colors = {"critical": "red", "warning": "yellow", "info": "blue"}
    icons = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
    
    card = (
        CardBuilder()
        .set_header(f"{icons[level]} {level.title()}", template=colors[level])
        .add_markdown(message)
    )
    
    if show_actions:
        card.add_button("Acknowledge", callback="ack")
    
    return card.build()
```

## Template Inheritance

### Base Templates

```yaml
templates:
  _base_alert:
    type: card
    header:
      title: "{icon} {title}"
      template: "{color}"
    elements:
      - type: markdown
        content: "{message}"
      - type: divider
      - type: note
        content: "Alert ID: {alert_id}"

  critical_alert:
    extends: _base_alert
    defaults:
      icon: "🚨"
      color: "red"

  warning_alert:
    extends: _base_alert
    defaults:
      icon: "⚠️"
      color: "yellow"
```

### Composition

```python
def compose_report_card(title: str, sections: list[dict]) -> dict:
    card = CardBuilder().set_header(title, template="blue")
    
    for section in sections:
        card.add_markdown(f"**{section['title']}**\n{section['content']}")
        card.add_divider()
    
    return card.build()
```

## Dynamic Templates

### Runtime Template Creation

```python
from feishu_webhook_bot.core.templates import Template

def create_dynamic_template(fields: list[str]) -> Template:
    field_content = "\n".join(f"**{f}:** {{{f}}}" for f in fields)
    
    return Template(
        name="dynamic",
        type="markdown",
        content=f"## Dynamic Report\n\n{field_content}"
    )

# Register and use
template = create_dynamic_template(["name", "status", "count"])
bot.template_registry.register(template)
bot.send_template("dynamic", name="Test", status="OK", count=42)
```

### Template Factory

```python
class AlertTemplateFactory:
    @staticmethod
    def create(level: str, include_actions: bool = True) -> dict:
        colors = {"critical": "red", "warning": "yellow", "info": "blue"}
        
        elements = [
            {"type": "markdown", "content": "{message}"},
            {"type": "divider"},
            {"type": "fields", "fields": [
                {"title": "Time", "value": "{timestamp}"},
                {"title": "Source", "value": "{source}"}
            ]}
        ]
        
        if include_actions:
            elements.append({
                "type": "actions",
                "actions": [
                    {"type": "button", "text": "Acknowledge", "callback": "ack"},
                    {"type": "button", "text": "Escalate", "callback": "escalate"}
                ]
            })
        
        return {
            "type": "card",
            "header": {"title": "{title}", "template": colors.get(level, "grey")},
            "elements": elements
        }
```

## Best Practices

### Template Organization

```text
templates/
├── alerts/
│   ├── critical.yaml
│   ├── warning.yaml
│   └── info.yaml
├── reports/
│   ├── daily.yaml
│   ├── weekly.yaml
│   └── monthly.yaml
├── notifications/
│   ├── welcome.yaml
│   └── reminder.yaml
└── _base.yaml
```

### Naming Conventions

- Use lowercase with underscores: `daily_report`, `critical_alert`
- Prefix internal/base templates with underscore: `_base_card`
- Group related templates: `alert_critical`, `alert_warning`

### Variable Naming

- Use descriptive names: `user_name` not `n`
- Use consistent casing: `snake_case` preferred
- Document required variables in comments

### Performance

```python
# Pre-compile templates for better performance
from feishu_webhook_bot.core.templates import CompiledTemplate

compiled = CompiledTemplate.compile(template_string)
result = compiled.render(name="John")
```

### Validation

```python
# Validate template before use
def validate_template(template: dict, required_vars: list[str]) -> bool:
    content = str(template)
    for var in required_vars:
        if f"{{{var}}}" not in content:
            return False
    return True
```

### Testing Templates

```python
import pytest
from feishu_webhook_bot.core.templates import TemplateRegistry

def test_alert_template():
    registry = TemplateRegistry.from_config("config.yaml")
    
    result = registry.render("alert",
        level="WARNING",
        title="Test",
        message="Test message"
    )
    
    assert "WARNING" in str(result)
    assert "Test message" in str(result)
```

## See Also

- [Message Types](message-types.md) - All message types
- [Configuration Reference](configuration-reference.md) - Template configuration
- [Examples](../resources/examples.md) - Template examples
