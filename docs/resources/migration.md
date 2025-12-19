# Migration Guide

Guide for migrating between versions of the Feishu Webhook Bot framework.

## Table of Contents

- [Version Compatibility](#version-compatibility)
- [Migrating to 1.0](#migrating-to-10)
- [Configuration Migration](#configuration-migration)
- [API Changes](#api-changes)
- [Plugin Migration](#plugin-migration)
- [Database Migration](#database-migration)
- [Rollback Procedures](#rollback-procedures)

## Version Compatibility

| From Version | To Version | Breaking Changes | Migration Difficulty |
|--------------|------------|------------------|---------------------|
| 0.1.x | 0.2.x | Minor | Easy |
| 0.2.x | 1.0.x | Major | Medium |

### Python Version Requirements

| Framework Version | Python Version |
|-------------------|----------------|
| 0.1.x | 3.9+ |
| 0.2.x | 3.10+ |
| 1.0.x | 3.10+ |

## Migrating to 1.0

### Overview of Changes

Version 1.0 introduces several breaking changes:

1. **Configuration format** - New structure for webhooks and providers
2. **API changes** - Renamed methods and new signatures
3. **Plugin system** - Updated lifecycle hooks
4. **Dependencies** - Updated to Pydantic v2

### Step-by-Step Migration

#### Step 1: Update Dependencies

```bash
# Update to latest version
uv add feishu-webhook-bot@latest

# Or with pip
pip install --upgrade feishu-webhook-bot
```

#### Step 2: Update Configuration

See [Configuration Migration](#configuration-migration) below.

#### Step 3: Update Code

See [API Changes](#api-changes) below.

#### Step 4: Update Plugins

See [Plugin Migration](#plugin-migration) below.

#### Step 5: Test

```bash
# Run tests
uv run pytest

# Test configuration
python -c "from feishu_webhook_bot.core import BotConfig; BotConfig.from_yaml('config.yaml')"
```

## Configuration Migration

### Webhook Configuration

**Before (0.x):**

```yaml
webhook_url: "https://open.feishu.cn/..."
webhook_secret: "secret"
```

**After (1.0):**

```yaml
webhooks:
  - name: default
    url: "https://open.feishu.cn/..."
    secret: "secret"
```

### Provider Configuration

**Before (0.x):**

```yaml
feishu:
  webhook_url: "https://..."

napcat:
  http_url: "http://..."
```

**After (1.0):**

```yaml
providers:
  - provider_type: feishu
    name: feishu-main
    url: "https://..."

  - provider_type: qq_napcat
    name: qq-main
    http_url: "http://..."

default_provider: feishu-main
```

### AI Configuration

**Before (0.x):**

```yaml
ai_enabled: true
ai_model: "gpt-4"
ai_api_key: "sk-..."
```

**After (1.0):**

```yaml
ai:
  enabled: true
  model: "openai:gpt-4o"
  api_key: "${OPENAI_API_KEY}"
```

### Scheduler Configuration

**Before (0.x):**

```yaml
scheduler:
  timezone: "Asia/Shanghai"
```

**After (1.0):**

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  job_store_type: "sqlite"
  job_store_path: "data/jobs.db"
```

### Plugin Configuration

**Before (0.x):**

```yaml
plugins:
  - name: my-plugin
    enabled: true
    config:
      setting1: value1
```

**After (1.0):**

```yaml
plugins:
  enabled: true
  plugin_dir: "plugins"
  plugin_settings:
    my-plugin:
      setting1: value1
```

### Migration Script

```python
"""Script to migrate config from 0.x to 1.0 format."""
import yaml

def migrate_config(old_config: dict) -> dict:
    new_config = {}

    # Migrate webhooks
    if "webhook_url" in old_config:
        new_config["webhooks"] = [{
            "name": "default",
            "url": old_config["webhook_url"],
            "secret": old_config.get("webhook_secret"),
        }]

    # Migrate AI
    if old_config.get("ai_enabled"):
        new_config["ai"] = {
            "enabled": True,
            "model": f"openai:{old_config.get('ai_model', 'gpt-4')}",
            "api_key": old_config.get("ai_api_key"),
        }

    # Migrate scheduler
    if "scheduler" in old_config:
        new_config["scheduler"] = {
            "enabled": True,
            **old_config["scheduler"],
        }

    # Migrate plugins
    if "plugins" in old_config:
        plugin_settings = {}
        for plugin in old_config["plugins"]:
            if plugin.get("config"):
                plugin_settings[plugin["name"]] = plugin["config"]

        new_config["plugins"] = {
            "enabled": True,
            "plugin_settings": plugin_settings,
        }

    return new_config

# Usage
with open("config.old.yaml") as f:
    old = yaml.safe_load(f)

new = migrate_config(old)

with open("config.yaml", "w") as f:
    yaml.dump(new, f, default_flow_style=False)
```

## API Changes

### Bot Class

**Before (0.x):**

```python
from feishu_webhook_bot import FeishuBot

bot = FeishuBot(webhook_url="https://...", secret="...")
bot.send("Hello!")
bot.send_card(card_dict)
```

**After (1.0):**

```python
from feishu_webhook_bot import FeishuBot

bot = FeishuBot.from_config("config.yaml")
bot.send_text("Hello!")
bot.send_card(card_dict)
```

### Client Class

**Before (0.x):**

```python
from feishu_webhook_bot import FeishuWebhookClient

client = FeishuWebhookClient(url="https://...", secret="...")
client.send_text("Hello")
```

**After (1.0):**

```python
from feishu_webhook_bot.core import FeishuWebhookClient, WebhookConfig

config = WebhookConfig(
    name="default",
    url="https://...",
    secret="...",
)
client = FeishuWebhookClient(config)
client.send_text("Hello")
```

### Scheduler

**Before (0.x):**

```python
from feishu_webhook_bot import scheduler

@scheduler.scheduled_job('interval', minutes=5)
def my_job():
    pass
```

**After (1.0):**

```python
from feishu_webhook_bot.scheduler import job

@job(trigger='interval', minutes=5)
def my_job():
    pass
```

### AI Agent

**Before (0.x):**

```python
response = bot.ai.chat("user123", "Hello")
```

**After (1.0):**

```python
response = await bot.ai_agent.chat("user123", "Hello")
# Note: Now async by default
```

### Method Renames

| Old Name | New Name |
|----------|----------|
| `bot.send()` | `bot.send_text()` |
| `bot.send_rich()` | `bot.send_rich_text()` |
| `client.post_message()` | `client.send_text()` |
| `plugin.setup()` | `plugin.on_enable()` |
| `plugin.teardown()` | `plugin.on_disable()` |

## Plugin Migration

### Lifecycle Hooks

**Before (0.x):**

```python
class MyPlugin(BasePlugin):
    def setup(self):
        # Initialize plugin
        pass

    def teardown(self):
        # Cleanup
        pass
```

**After (1.0):**

```python
class MyPlugin(BasePlugin):
    def on_enable(self) -> None:
        # Initialize plugin
        pass

    def on_disable(self) -> None:
        # Cleanup
        pass

    def on_reload(self) -> None:
        # Handle hot-reload
        pass
```

### Metadata

**Before (0.x):**

```python
class MyPlugin(BasePlugin):
    name = "my-plugin"
    version = "1.0.0"
```

**After (1.0):**

```python
class MyPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="My plugin description",
            author="Your Name",
        )
```

### Configuration Access

**Before (0.x):**

```python
class MyPlugin(BasePlugin):
    def setup(self):
        value = self.config.get("setting1")
```

**After (1.0):**

```python
class MyPlugin(BasePlugin):
    def on_enable(self):
        value = self.get_config("setting1", default="default_value")
```

### Job Registration

**Before (0.x):**

```python
class MyPlugin(BasePlugin):
    def setup(self):
        self.scheduler.add_job(self.my_task, 'interval', minutes=5)
```

**After (1.0):**

```python
class MyPlugin(BasePlugin):
    def on_enable(self):
        self.register_job(
            self.my_task,
            trigger='interval',
            minutes=5,
            id='my-plugin-task',
        )
```

## Database Migration

### Auth Database

If using the authentication system, migrate the database:

```python
"""Migrate auth database from 0.x to 1.0."""
import sqlite3

def migrate_auth_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add new columns
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
        cursor.execute("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP")
        cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # Columns already exist

    # Update existing rows
    cursor.execute("""
        UPDATE users
        SET created_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
    """)

    conn.commit()
    conn.close()

migrate_auth_db("data/auth.db")
```

### Message Tracking Database

```python
"""Migrate message tracking database."""
import sqlite3

def migrate_messages_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add provider column
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN provider TEXT DEFAULT 'feishu'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
```

## Rollback Procedures

### Before Migration

1. **Backup configuration:**

   ```bash
   cp config.yaml config.yaml.backup
   ```

2. **Backup database:**

   ```bash
   cp -r data/ data.backup/
   ```

3. **Record current version:**

   ```bash
   pip show feishu-webhook-bot > version.txt
   ```

### Rollback Steps

1. **Restore configuration:**

   ```bash
   cp config.yaml.backup config.yaml
   ```

2. **Restore database:**

   ```bash
   rm -rf data/
   cp -r data.backup/ data/
   ```

3. **Downgrade package:**

   ```bash
   pip install feishu-webhook-bot==0.2.0
   ```

4. **Verify rollback:**

   ```bash
   python -c "from feishu_webhook_bot import FeishuBot; print('OK')"
   ```

### Rollback Script

```bash
#!/bin/bash
# rollback.sh

set -e

echo "Rolling back to previous version..."

# Restore config
if [ -f config.yaml.backup ]; then
    cp config.yaml.backup config.yaml
    echo "Configuration restored"
fi

# Restore data
if [ -d data.backup ]; then
    rm -rf data/
    cp -r data.backup/ data/
    echo "Data restored"
fi

# Downgrade package
if [ -f version.txt ]; then
    VERSION=$(grep "Version:" version.txt | cut -d' ' -f2)
    pip install feishu-webhook-bot==$VERSION
    echo "Package downgraded to $VERSION"
fi

echo "Rollback complete"
```

## See Also

- [Changelog](changelog.md) - Version history
- [Installation](../getting-started/installation.md) - Installation guide
- [Configuration Reference](../guides/configuration-reference.md) - Configuration options
