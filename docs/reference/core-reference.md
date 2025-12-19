# Core Components Reference

This document provides detailed documentation for the core components of the Feishu Webhook Bot framework.

## Table of Contents

- [Circuit Breaker](#circuit-breaker)
- [Message Queue](#message-queue)
- [Message Tracker](#message-tracker)
- [Configuration Watcher](#configuration-watcher)
- [Image Uploader](#image-uploader)
- [Provider Abstraction](#provider-abstraction)
- [Configuration Validation](#configuration-validation)
- [Message Handler](#message-handler)
- [Message Parsers](#message-parsers)

## Circuit Breaker

The circuit breaker pattern prevents cascading failures when external services are unavailable.

### Overview

The circuit breaker has three states:

1. **Closed**: Normal operation, requests pass through
2. **Open**: Service is unavailable, requests fail immediately
3. **Half-Open**: Testing if service has recovered

### Configuration

```yaml
# In webhook or provider configuration
circuit_breaker:
  failure_threshold: 5      # Failures before opening circuit
  reset_timeout: 30.0       # Seconds before attempting recovery
  half_open_max_calls: 3    # Max calls in half-open state
```

### Usage

```python
from feishu_webhook_bot.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    circuit_breaker,
)

# Create a circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,
    reset_timeout=30.0,
    half_open_max_calls=3,
)
breaker = CircuitBreaker(config)

# Use as context manager
async with breaker:
    result = await external_service_call()

# Or use the decorator
@circuit_breaker(failure_threshold=5, reset_timeout=30.0)
async def call_external_service():
    return await external_service_call()

# Use the registry for named circuit breakers
registry = CircuitBreakerRegistry()
registry.register("webhook", config)
breaker = registry.get("webhook")
```

### States and Transitions

```text
┌─────────┐  failure_threshold  ┌──────┐
│ CLOSED  │ ─────────────────→  │ OPEN │
└─────────┘                     └──────┘
     ↑                              │
     │                              │ reset_timeout
     │                              ↓
     │                        ┌───────────┐
     │  success               │ HALF_OPEN │
     └─────────────────────── └───────────┘
```

### Exception Handling

```python
from feishu_webhook_bot.core.circuit_breaker import CircuitBreakerOpen

try:
    async with breaker:
        result = await risky_operation()
except CircuitBreakerOpen:
    # Circuit is open, use fallback
    result = fallback_value
```

## Message Queue

The message queue provides async message delivery with retry support.

### Overview

- **Async Processing**: Messages are queued and processed asynchronously
- **Retry Logic**: Failed messages are automatically retried
- **Batch Processing**: Messages can be processed in batches
- **Priority Support**: Messages can have different priorities

### Configuration

```yaml
message_queue:
  enabled: true
  max_batch_size: 10      # Messages per batch
  retry_delay: 5.0        # Base delay for retries (seconds)
  max_retries: 3          # Maximum retry attempts
```

### Usage

```python
from feishu_webhook_bot.core.message_queue import MessageQueue, QueuedMessage

# Create queue
queue = MessageQueue(
    max_batch_size=10,
    retry_delay=5.0,
    max_retries=3,
)

# Add message to queue
message = QueuedMessage(
    webhook_name="default",
    message_type="text",
    content={"text": "Hello, World!"},
    priority=1,  # Lower = higher priority
)
await queue.enqueue(message)

# Start processing
await queue.start()

# Stop processing
await queue.stop()
```

### Message States

| State | Description |
|-------|-------------|
| `pending` | Message is waiting to be sent |
| `sending` | Message is being sent |
| `sent` | Message was sent successfully |
| `failed` | Message failed after all retries |
| `retrying` | Message is waiting for retry |

## Message Tracker

The message tracker provides delivery tracking and deduplication.

### Overview

- **Delivery Tracking**: Track message delivery status
- **Deduplication**: Prevent duplicate message processing
- **Persistence**: Optionally persist tracking data to SQLite
- **Analytics**: Get message delivery statistics

### Configuration

```yaml
message_tracking:
  enabled: true
  max_history: 10000      # Max messages to track in memory
  cleanup_interval: 3600  # Cleanup interval (seconds)
  db_path: "data/messages.db"  # SQLite path (null for in-memory)
```

### Usage

```python
from feishu_webhook_bot.core.message_tracker import (
    MessageTracker,
    MessageStatus,
    TrackedMessage,
)

# Create tracker
tracker = MessageTracker(
    max_history=10000,
    cleanup_interval=3600,
    db_path="data/messages.db",
)

# Track a message
message_id = await tracker.track_message(
    webhook_name="default",
    message_type="text",
    content={"text": "Hello"},
)

# Update status
await tracker.update_status(message_id, MessageStatus.SENT)

# Check if message was already processed (deduplication)
if await tracker.is_duplicate(event_id):
    return  # Skip duplicate

# Get message info
message = await tracker.get_message(message_id)
print(f"Status: {message.status}")

# Get statistics
stats = await tracker.get_stats()
print(f"Total: {stats['total']}, Sent: {stats['sent']}, Failed: {stats['failed']}")
```

### Message Status

| Status | Description |
|--------|-------------|
| `pending` | Message created, not yet sent |
| `sending` | Message is being sent |
| `sent` | Message delivered successfully |
| `failed` | Message delivery failed |
| `expired` | Message expired before delivery |

## Configuration Watcher

The configuration watcher enables hot-reload of configuration changes.

### Overview

- **File Watching**: Monitor config file for changes
- **Auto-Reload**: Automatically reload configuration
- **Validation**: Validate new configuration before applying
- **Callbacks**: Execute callbacks on configuration change

### Configuration

```yaml
config_hot_reload: true  # Enable hot-reload
```

### Usage

```python
from feishu_webhook_bot.core.config_watcher import (
    ConfigWatcher,
    create_config_watcher,
)

# Create watcher
watcher = create_config_watcher(
    config_path="config.yaml",
    bot=bot,  # FeishuBot instance
)

# Start watching
watcher.start()

# Add custom callback
def on_config_change(new_config):
    print("Configuration changed!")
    # Handle configuration change

watcher.add_callback(on_config_change)

# Stop watching
watcher.stop()
```

### Events

The watcher triggers on:

- File modification
- File creation (if watching a directory)
- File deletion (logs warning)

## Image Uploader

The image uploader provides utilities for uploading images to Feishu.

### Overview

- **Image Upload**: Upload images to Feishu and get image keys
- **Permission Check**: Verify upload permissions
- **Card Creation**: Create image cards from uploaded images

### Usage

```python
from feishu_webhook_bot.core.image_uploader import (
    FeishuImageUploader,
    FeishuPermissionChecker,
    create_image_card,
)

# Create uploader (requires app credentials)
uploader = FeishuImageUploader(
    app_id="your-app-id",
    app_secret="your-app-secret",
)

# Upload image
image_key = await uploader.upload_image("path/to/image.png")

# Create image card
card = create_image_card(
    image_key=image_key,
    alt_text="My Image",
    title="Image Title",
)

# Check permissions
checker = FeishuPermissionChecker(app_id, app_secret)
has_permission = await checker.check_image_upload_permission()
```

### Supported Formats

- PNG
- JPEG/JPG
- GIF
- BMP
- WebP

### Error Handling

```python
from feishu_webhook_bot.core.image_uploader import (
    FeishuImageUploaderError,
    FeishuPermissionDeniedError,
)

try:
    image_key = await uploader.upload_image("image.png")
except FeishuPermissionDeniedError:
    print("No permission to upload images")
except FeishuImageUploaderError as e:
    print(f"Upload failed: {e}")
```

## Provider Abstraction

The provider abstraction layer enables multi-platform message delivery.

### Overview

- **Unified Interface**: Common interface for all providers
- **Multiple Platforms**: Support for Feishu, QQ/Napcat, and custom providers
- **Provider Registry**: Manage multiple provider instances

### Base Provider

```python
from feishu_webhook_bot.core.provider import (
    BaseProvider,
    Message,
    MessageType,
    ProviderConfig,
    SendResult,
)

class CustomProvider(BaseProvider):
    """Custom message provider implementation."""

    async def send_message(self, message: Message) -> SendResult:
        """Send a message through this provider."""
        # Implementation
        pass

    async def start(self) -> None:
        """Start the provider."""
        pass

    async def stop(self) -> None:
        """Stop the provider."""
        pass
```

### Message Types

| Type | Description |
|------|-------------|
| `text` | Plain text message |
| `rich_text` | Rich text with formatting |
| `card` | Interactive card |
| `image` | Image message |
| `file` | File attachment |

### Provider Registry

```python
from feishu_webhook_bot.core.provider import ProviderRegistry

registry = ProviderRegistry()

# Register providers
registry.register("feishu", feishu_provider)
registry.register("qq", napcat_provider)

# Get provider
provider = registry.get("feishu")

# Send message
result = await provider.send_message(message)
```

## Configuration Validation

The validation module provides utilities for validating configuration files.

### Overview

- **JSON Schema**: Generate and validate against JSON schema
- **Completeness Check**: Check configuration completeness
- **Error Reporting**: Detailed validation error messages

### Usage

```python
from feishu_webhook_bot.core.validation import (
    validate_yaml_config,
    generate_json_schema,
    check_config_completeness,
)

# Validate configuration
is_valid, errors = validate_yaml_config("config.yaml")
if not is_valid:
    for error in errors:
        print(f"Validation error: {error}")

# Generate JSON schema
schema = generate_json_schema("config-schema.json")

# Check completeness
info = check_config_completeness("config.yaml")
print(f"Completeness: {info['completeness_percentage']}%")
print(f"Missing sections: {info['missing_sections']}")
print(f"Recommendations: {info['recommendations']}")
```

### Validation Rules

The validator checks:

- Required fields are present
- Field types are correct
- Values are within allowed ranges
- URLs are valid format
- Cron expressions are valid
- Dependencies are satisfied

## Message Handler

The message handler module provides a unified interface for handling incoming messages from multiple platforms.

### Overview

- **IncomingMessage**: Universal message representation
- **MessageHandler**: Protocol for message handlers
- **MessageParser**: Protocol for platform-specific parsers
- **Utility functions**: User/chat key generation

### IncomingMessage

Universal incoming message representation across platforms.

```python
from feishu_webhook_bot.core.message_handler import IncomingMessage

# Create a message
msg = IncomingMessage(
    id="om_xxxxx",
    platform="feishu",
    chat_type="group",  # "private", "group", "channel"
    chat_id="oc_xxxxx",
    sender_id="ou_xxxxx",
    sender_name="Alice",
    content="Hello @bot",
    mentions=["bot_id"],
    is_at_bot=True,
    reply_to=None,
    thread_id=None,
)

# Serialize to dict
data = msg.to_dict()

# Deserialize from dict
msg = IncomingMessage.from_dict(data)
```

### Message Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Platform-specific message ID |
| `platform` | `Literal["feishu", "qq"]` | Source platform |
| `chat_type` | `Literal["private", "group", "channel"]` | Chat type |
| `chat_id` | `str` | Group/channel ID (empty for private) |
| `sender_id` | `str` | User ID on the platform |
| `sender_name` | `str` | Display name or username |
| `content` | `str` | Text content of the message |
| `mentions` | `list[str]` | List of @mentioned user IDs |
| `is_at_bot` | `bool` | Whether the bot is @mentioned |
| `reply_to` | `str \| None` | Message ID being replied to |
| `thread_id` | `str \| None` | Thread or topic ID |
| `timestamp` | `datetime` | Message creation timestamp |
| `raw_content` | `Any` | Platform-specific raw content |
| `metadata` | `dict[str, Any]` | Additional platform-specific data |

### User and Chat Keys

Generate unique keys for conversation tracking:

```python
from feishu_webhook_bot.core.message_handler import get_user_key, get_chat_key

# User key: platform:chat_type:sender_id
user_key = get_user_key(msg)
# "feishu:group:ou_xxxxx"

# Chat key: platform:chat_id (or sender_id for private)
chat_key = get_chat_key(msg)
# "feishu:oc_xxxxx"
```

## Message Parsers

Platform-specific parsers that convert raw webhook payloads to `IncomingMessage`.

### FeishuMessageParser

Parse Feishu event callbacks:

```python
from feishu_webhook_bot.core.message_parsers import (
    FeishuMessageParser,
    create_feishu_parser,
)

# Create parser
parser = FeishuMessageParser(bot_open_id="ou_bot_xxx")
# Or use factory
parser = create_feishu_parser(bot_open_id="ou_bot_xxx")

# Check if payload can be parsed
if parser.can_parse(payload):
    message = parser.parse(payload)
    if message:
        print(f"Message from {message.sender_name}: {message.content}")
```

### QQMessageParser

Parse OneBot11 events from QQ/Napcat:

```python
from feishu_webhook_bot.core.message_parsers import (
    QQMessageParser,
    create_qq_parser,
)

# Create parser
parser = QQMessageParser(bot_qq="123456789")
# Or use factory
parser = create_qq_parser(bot_qq="123456789")

# Parse message
if parser.can_parse(payload):
    message = parser.parse(payload)
    if message:
        print(f"Message from {message.sender_name}: {message.content}")
```

### Supported Event Formats

#### Feishu v2.0 Schema

```json
{
    "schema": "2.0",
    "header": {
        "event_id": "xxx",
        "event_type": "im.message.receive_v1",
        "create_time": "1234567890000"
    },
    "event": {
        "sender": {
            "sender_id": {"open_id": "ou_xxx"},
            "sender_type": "user"
        },
        "message": {
            "message_id": "om_xxx",
            "chat_id": "oc_xxx",
            "chat_type": "group",
            "message_type": "text",
            "content": "{\"text\":\"Hello\"}"
        }
    }
}
```

#### OneBot11 Format

```json
{
    "post_type": "message",
    "message_type": "group",
    "user_id": 987654321,
    "group_id": 123456,
    "message_id": 12345,
    "message": [
        {"type": "text", "data": {"text": "Hello"}}
    ],
    "sender": {
        "user_id": 987654321,
        "nickname": "Alice"
    }
}
```

### Custom Parser Implementation

```python
from feishu_webhook_bot.core.message_handler import IncomingMessage, MessageParser

class CustomParser:
    """Custom message parser for a new platform."""

    def __init__(self, bot_id: str | None = None):
        self.bot_id = bot_id

    def can_parse(self, payload: dict) -> bool:
        return payload.get("platform") == "custom"

    def parse(self, payload: dict) -> IncomingMessage | None:
        if not self.can_parse(payload):
            return None

        return IncomingMessage(
            id=payload["message_id"],
            platform="custom",
            chat_type="group",
            chat_id=payload["chat_id"],
            sender_id=payload["sender_id"],
            sender_name=payload["sender_name"],
            content=payload["text"],
        )

# Type check
parser: MessageParser = CustomParser()
```

## Best Practices

### Circuit Breaker

1. **Set appropriate thresholds**: Too low causes false positives, too high delays failure detection
2. **Use meaningful reset timeouts**: Allow enough time for services to recover
3. **Implement fallbacks**: Always have a fallback when circuit is open

### Message Queue

1. **Set reasonable batch sizes**: Balance throughput and memory usage
2. **Configure retry delays**: Use exponential backoff for retries
3. **Monitor queue depth**: Alert if queue grows too large

### Message Tracker

1. **Set appropriate history limits**: Balance tracking coverage and memory
2. **Use persistence for production**: Enable SQLite for crash recovery
3. **Regular cleanup**: Configure cleanup interval to prevent memory bloat

### Configuration Watcher

1. **Validate before applying**: Always validate new configuration
2. **Handle errors gracefully**: Don't crash on invalid configuration
3. **Log changes**: Log all configuration changes for auditing

## See Also

- [API Reference](api.md) - Complete API documentation
- [YAML Configuration Guide](../guides/yaml-configuration-guide.md) - Configuration reference
- [Providers Guide](../guides/providers-guide.md) - Multi-provider setup
