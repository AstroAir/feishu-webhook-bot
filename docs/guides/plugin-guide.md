# Plugin Development Guide

This guide explains how to develop custom plugins for the Feishu Webhook Bot framework.

## Table of Contents

- [Overview](#overview)
- [Plugin Structure](#plugin-structure)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Scheduling Tasks](#scheduling-tasks)
- [Sending Messages](#sending-messages)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [Built-in Plugins](#built-in-plugins)

## Overview

Plugins are Python classes that extend the `BasePlugin` class. They allow you to:

- Schedule periodic or cron-based tasks
- Send messages to Feishu webhooks
- Access bot configuration
- Handle lifecycle events
- Hot-reload without restarting the bot

## Plugin Structure

### Minimum Plugin

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="Description of my plugin",
            author="Your Name",
            enabled=True
        )
    
    def on_enable(self) -> None:
        self.logger.info("Plugin enabled")
```

### Plugin Metadata

The `metadata()` method must return a `PluginMetadata` instance with:

- `name` (str): Unique plugin identifier (required)
- `version` (str): Version string (default: "1.0.0")
- `description` (str): Brief description (optional)
- `author` (str): Author name (optional)
- `enabled` (bool): Whether plugin is enabled by default (default: True)

## Event Handling

Plugins can handle incoming Feishu webhook events when the event server is enabled.

### Handling Events

Implement the `handle_event()` method to react to Feishu events:

```python
def handle_event(self, event: dict[str, Any]) -> None:
    """Handle incoming Feishu webhook events.

    Args:
        event: Event payload from Feishu
    """
    event_type = event.get("header", {}).get("event_type")

    if event_type == "im.message.receive_v1":
        # Handle message received
        message = event.get("event", {}).get("message", {})
        content = message.get("content", "")
        self.client.send_text(f"Received: {content}")

    elif event_type == "im.chat.member_bot_added_v1":
        # Handle bot added to chat
        self.client.send_text("Thanks for adding me to this chat!")
```

### Common Event Types

- `im.message.receive_v1` - Message received in chat
- `im.chat.member_bot_added_v1` - Bot added to chat
- `im.chat.member_bot_deleted_v1` - Bot removed from chat
- `im.message.message_read_v1` - Message read
- `contact.user.created_v3` - User created
- `contact.user.updated_v3` - User updated

### Example: Message Echo Plugin

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from typing import Any

class EchoPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="echo-plugin",
            version="1.0.0",
            description="Echoes received messages"
        )

    def handle_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("header", {}).get("event_type")

        if event_type == "im.message.receive_v1":
            message = event.get("event", {}).get("message", {})
            content = message.get("content", "")

            # Echo the message back
            self.client.send_text(f"Echo: {content}")
```

## Lifecycle Hooks

### on_load()

Called when the plugin is first loaded from disk.

**Use for:**

- Reading configuration
- Initializing variables
- Setting up data structures

```python
def on_load(self) -> None:
    self.logger.info("Plugin loaded")
    self.counter = 0
    self.my_config = self.get_config_value("my_setting", "default")
```

### on_enable()

Called when the plugin is enabled and the bot is running.

**Use for:**

- Registering scheduled jobs
- Setting up resources
- Starting background tasks

```python
def on_enable(self) -> None:
    self.logger.info("Plugin enabled")
    
    # Register scheduled jobs
    self.register_job(
        self.my_task,
        trigger='interval',
        minutes=5
    )
```

### on_disable()

Called when the plugin is disabled or the bot is shutting down.

**Use for:**

- Cleaning up resources
- Saving state
- Closing connections

```python
def on_disable(self) -> None:
    self.logger.info("Plugin disabled")
    # Save state, close connections, etc.
```

### on_unload()

Called when the plugin is unloaded (typically before hot-reload).

**Use for:**

- Final cleanup before reload
- Closing file handles
- Releasing locks

```python
def on_unload(self) -> None:
    self.logger.info("Plugin unloaded")
```

## Scheduling Tasks

### Interval-based Scheduling

Run a task at regular intervals:

```python
def on_enable(self) -> None:
    # Run every 5 minutes
    self.register_job(
        self.my_task,
        trigger='interval',
        minutes=5
    )
    
    # Run every 30 seconds
    self.register_job(
        self.frequent_task,
        trigger='interval',
        seconds=30
    )
    
    # Run every 2 hours
    self.register_job(
        self.hourly_task,
        trigger='interval',
        hours=2
    )
```

### Cron-based Scheduling

Use cron expressions for specific times:

```python
def on_enable(self) -> None:
    # Daily at 9:00 AM
    self.register_job(
        self.morning_task,
        trigger='cron',
        hour='9',
        minute='0'
    )
    
    # Every Monday at 10:30 AM
    self.register_job(
        self.weekly_task,
        trigger='cron',
        day_of_week='mon',
        hour='10',
        minute='30'
    )
    
    # Weekdays at 6:00 PM
    self.register_job(
        self.evening_task,
        trigger='cron',
        day_of_week='mon-fri',
        hour='18',
        minute='0'
    )
    
    # First day of month at midnight
    self.register_job(
        self.monthly_task,
        trigger='cron',
        day='1',
        hour='0',
        minute='0'
    )
```

### Custom Job IDs

Provide custom job IDs for better control:

```python
def on_enable(self) -> None:
    self.register_job(
        self.my_task,
        trigger='interval',
        minutes=10,
        job_id='my_custom_job_id'
    )
```

## Sending Messages

### Text Messages

```python
def my_task(self) -> None:
    self.client.send_text("Hello, Feishu!")
```

### Rich Text Messages

```python
def my_task(self) -> None:
    content = [
        [
            {"tag": "text", "text": "Hello "},
            {"tag": "a", "text": "click here", "href": "https://example.com"}
        ]
    ]
    self.client.send_rich_text("Title", content)
```

### Interactive Cards

Using CardBuilder:

```python
from feishu_webhook_bot.core.client import CardBuilder

def my_task(self) -> None:
    card = (
        CardBuilder()
        .set_config(wide_screen_mode=True)
        .set_header("Notification", template="blue")
        .add_markdown("**Important:** Message content")
        .add_divider()
        .add_text("Additional information")
        .add_button("View Details", url="https://example.com")
        .add_note("Footer note")
        .build()
    )
    self.client.send_card(card)
```

### Card Templates

Available header templates:

- `blue` (default)
- `red`
- `orange`
- `yellow`
- `green`
- `turquoise`
- `purple`

```python
# Success card
card = CardBuilder().set_header("Success", template="green")

# Alert card
card = CardBuilder().set_header("Alert", template="red")

# Warning card
card = CardBuilder().set_header("Warning", template="orange")
```

## Configuration

### Reading Configuration

Plugins can access bot configuration:

```python
def on_load(self) -> None:
    # Access webhook config
    webhook = self.config.get_webhook("default")

    # Get custom config value
    my_value = self.get_config_value("my_key", default="default_value")
```

### Plugin-specific Configuration

You can add plugin-specific configuration to `config.yaml`:

```yaml
# config.yaml
plugins:
  enabled: true
  plugin_dir: "plugins"
  auto_reload: true

  # Plugin-specific settings
  plugin_settings:
    - plugin_name: "my-plugin"
      enabled: true
      priority: 10  # Lower numbers load first
      settings:
        api_key: "xxx"
        threshold: 80
        check_interval: 300

    - plugin_name: "another-plugin"
      enabled: true
      priority: 50
      settings:
        custom_setting: "value"
```

Access in plugin:

```python
class MyPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="my-plugin", version="1.0.0")

    def on_load(self) -> None:
        # Get specific setting
        api_key = self.get_config_value("api_key", "default_key")
        threshold = self.get_config_value("threshold", 50)

        # Get all settings
        all_settings = self.get_all_config()

        self.logger.info(f"Loaded with threshold: {threshold}")
```

### Plugin Loading Priority

Plugins are loaded in order of their `priority` value (lower numbers first):

```yaml
plugin_settings:
  - plugin_name: "database-plugin"
    priority: 10  # Loads first

  - plugin_name: "api-plugin"
    priority: 20  # Loads second

  - plugin_name: "notification-plugin"
    priority: 100  # Loads last (default)
```

### Disabling Plugins

Disable specific plugins without removing them:

```yaml
plugin_settings:
  - plugin_name: "my-plugin"
    enabled: false  # Plugin won't be loaded
```

## Best Practices

### Error Handling

Always wrap task code in try-except blocks:

```python
def my_task(self) -> None:
    try:
        # Your code here
        result = self.do_something()
        self.client.send_text(f"Success: {result}")
        
    except Exception as e:
        self.logger.error(f"Task failed: {e}", exc_info=True)
        # Optionally send error notification
        self.client.send_text(f"❌ Error: {str(e)}")
```

### Logging

Use the provided logger for all logging:

```python
def my_task(self) -> None:
    self.logger.debug("Debug information")
    self.logger.info("Informational message")
    self.logger.warning("Warning message")
    self.logger.error("Error message")
```

### Resource Management

Clean up resources in `on_disable()`:

```python
def on_load(self) -> None:
    self.db_connection = None

def on_enable(self) -> None:
    self.db_connection = connect_to_database()

def on_disable(self) -> None:
    if self.db_connection:
        self.db_connection.close()
        self.db_connection = None
```

### State Management

Store persistent state between runs:

```python
import json
from pathlib import Path

def on_load(self) -> None:
    self.state_file = Path("data/my_plugin_state.json")
    self.state = self.load_state()

def load_state(self) -> dict:
    if self.state_file.exists():
        return json.loads(self.state_file.read_text())
    return {}

def save_state(self) -> None:
    self.state_file.parent.mkdir(exist_ok=True)
    self.state_file.write_text(json.dumps(self.state))

def on_disable(self) -> None:
    self.save_state()
```

## Examples

### Example 1: Simple Reminder

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class ReminderPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="simple-reminder",
            version="1.0.0",
            description="Sends a reminder every hour"
        )
    
    def on_enable(self) -> None:
        self.register_job(
            self.send_reminder,
            trigger='interval',
            hours=1
        )
    
    def send_reminder(self) -> None:
        self.client.send_text("⏰ Hourly reminder: Take a break!")
```

### Example 2: API Monitor

```python
import httpx
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from feishu_webhook_bot.core.client import CardBuilder

class APIMonitorPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="api-monitor",
            version="1.0.0",
            description="Monitors API endpoints"
        )
    
    def on_load(self) -> None:
        self.endpoints = [
            "https://api.example.com/health",
            "https://api2.example.com/status"
        ]
    
    def on_enable(self) -> None:
        # Check every 5 minutes
        self.register_job(
            self.check_endpoints,
            trigger='interval',
            minutes=5
        )
    
    def check_endpoints(self) -> None:
        for url in self.endpoints:
            try:
                response = httpx.get(url, timeout=10)
                if response.status_code != 200:
                    self.send_alert(url, response.status_code)
            except Exception as e:
                self.send_alert(url, str(e))
    
    def send_alert(self, url: str, error: str) -> None:
        card = (
            CardBuilder()
            .set_header("🚨 API Alert", template="red")
            .add_markdown(f"**Endpoint:** {url}\n**Error:** {error}")
            .build()
        )
        self.client.send_card(card)
```

### Example 3: Data Reporter

```python
from datetime import datetime
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from feishu_webhook_bot.core.client import CardBuilder

class DataReporterPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="data-reporter",
            version="1.0.0",
            description="Sends daily data reports"
        )
    
    def on_enable(self) -> None:
        # Daily report at 9 AM
        self.register_job(
            self.send_daily_report,
            trigger='cron',
            hour='9',
            minute='0'
        )
    
    def send_daily_report(self) -> None:
        # Fetch your data
        data = self.fetch_daily_data()
        
        # Build report card
        card = (
            CardBuilder()
            .set_header("📊 Daily Report", template="blue")
            .add_markdown(
                f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n"
                f"**Users:** {data['users']}\n"
                f"**Revenue:** ${data['revenue']}"
            )
            .add_divider()
            .add_button("View Dashboard", url="https://dashboard.example.com")
            .build()
        )
        
        self.client.send_card(card)
    
    def fetch_daily_data(self) -> dict:
        # Your data fetching logic
        return {
            "users": 1234,
            "revenue": 5678.90
        }
```

## Built-in Plugins

The framework includes several built-in plugins that demonstrate advanced capabilities.

### RSS Subscription Plugin

AI-enhanced RSS feed monitoring with summarization and classification.

**Features:**

- Multiple feed support with per-feed configuration
- AI-powered summarization, classification, and keyword extraction
- Intelligent aggregation for batch notifications
- Beautiful card-based display
- Command interface for managing subscriptions

**Configuration:**

```yaml
plugins:
  rss_subscription:
    enabled: true
    feeds:
      - name: "Tech News"
        url: "https://example.com/feed.xml"
        check_interval_minutes: 30
        max_entries: 10
        tags: ["tech", "news"]
        webhook_target: "default"
    ai_summarization: true
    ai_classification: true
    aggregation_enabled: true
    aggregation_interval_minutes: 60
```

**Commands:**

| Command | Description |
|---------|-------------|
| `/rss list` | List all subscribed feeds |
| `/rss add <url>` | Add a new feed |
| `/rss remove <name>` | Remove a feed |
| `/rss check <name>` | Force check a feed |

### Feishu Calendar Plugin

Comprehensive calendar integration with Feishu Open Platform.

**Features:**

- Periodically checking Feishu calendar events
- Sending reminders for upcoming events
- Supporting multiple calendars and reminder times
- Beautiful card-based event display
- Daily/weekly agenda summaries

**Configuration:**

```yaml
plugins:
  feishu_calendar:
    enabled: true
    app_id: "${FEISHU_APP_ID}"
    app_secret: "${FEISHU_APP_SECRET}"
    calendars:
      - calendar_id: "primary"
        name: "My Calendar"
        reminder_minutes: [15, 60]
    check_interval_minutes: 5
    daily_agenda_time: "08:00"
    weekly_agenda_day: "monday"
```

**Commands:**

| Command | Description |
|---------|-------------|
| `/calendar today` | Show today's events |
| `/calendar week` | Show this week's events |
| `/calendar next` | Show next upcoming event |

### System Monitor Plugin

Monitor system resources and send alerts.

**Configuration:**

```yaml
plugins:
  system_monitor:
    enabled: true
    check_interval_minutes: 5
    cpu_threshold: 80
    memory_threshold: 85
    disk_threshold: 90
```

### Daily Greeting Plugin

Send daily greeting messages at configured times.

**Configuration:**

```yaml
plugins:
  daily_greeting:
    enabled: true
    greeting_time: "09:00"
    greeting_message: "Good morning! Have a productive day!"
```

### Reminder Plugin

Set and manage reminders.

**Commands:**

| Command | Description |
|---------|-------------|
| `/remind <time> <message>` | Set a reminder |
| `/remind list` | List pending reminders |
| `/remind cancel <id>` | Cancel a reminder |

## Testing Your Plugin

1. Create your plugin file in `plugins/` directory
2. Start the bot with `feishu-webhook-bot start`
3. Watch the logs for plugin loading and execution
4. Plugin will hot-reload automatically when you edit the file

## Troubleshooting

### Plugin not loading

- Check that the filename doesn't start with underscore
- Verify the class inherits from `BasePlugin`
- Check logs for error messages

### Jobs not executing

- Verify scheduler is enabled in config
- Check timezone settings
- Look for errors in logs during job execution

### Hot-reload not working

- Ensure `auto_reload: true` in config
- Check that `plugin_dir` path is correct
- Verify watchdog is installed

## Next Steps

- Check out the example plugins in the repository for more inspiration
- Read the [API Reference](../reference/api.md) for detailed API documentation
- Join our community for help and discussions
