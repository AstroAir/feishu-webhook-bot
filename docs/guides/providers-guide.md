# Multi-Provider Guide

This guide explains how to configure and use multiple message providers in the Feishu Webhook Bot framework.

## Table of Contents

- [Overview](#overview)
- [Supported Providers](#supported-providers)
- [Configuration](#configuration)
- [Feishu Provider](#feishu-provider)
- [Feishu Open Platform API](#feishu-open-platform-api)
- [QQ/Napcat Provider](#qqnapcat-provider)
- [QQ Event Handler](#qq-event-handler)
- [Custom Providers](#custom-providers)
- [Provider Registry](#provider-registry)
- [Best Practices](#best-practices)

## Overview

The multi-provider architecture allows you to send messages to different platforms from a single bot instance:

- **Unified Interface**: Common `Message` and `SendResult` types across all providers
- **Provider Registry**: Manage multiple provider instances
- **Circuit Breaker**: Built-in fault tolerance for each provider
- **Message Tracking**: Optional delivery tracking per provider

## Supported Providers

| Provider | Platform | Protocol | Features |
|----------|----------|----------|----------|
| **FeishuProvider** | Feishu/Lark | Webhook API | Text, Rich Text, Cards, Images |
| **NapcatProvider** | QQ | OneBot11 | Text, Rich Text, Images |
| **Custom** | Any | HTTP | Extensible base class |

## Configuration

### YAML Configuration

```yaml
# Multi-provider configuration
providers:
  - provider_type: "feishu"
    name: "feishu-main"
    enabled: true
    webhook_url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_WEBHOOK_SECRET}"
    timeout: 10.0
    circuit_breaker:
      failure_threshold: 5
      reset_timeout: 30.0
    message_tracking: true

  - provider_type: "napcat"
    name: "qq-group"
    enabled: true
    http_url: "http://127.0.0.1:3000"
    access_token: "${NAPCAT_ACCESS_TOKEN}"
    default_target: "group:123456789"
    timeout: 10.0

default_provider: "feishu-main"
```

### Python Configuration

```python
from feishu_webhook_bot.core.config import BotConfig, ProviderConfigBase

config = BotConfig(
    providers=[
        ProviderConfigBase(
            provider_type="feishu",
            name="feishu-main",
            webhook_url="https://open.feishu.cn/...",
            secret="your-secret",
        ),
        ProviderConfigBase(
            provider_type="napcat",
            name="qq-group",
            http_url="http://127.0.0.1:3000",
            access_token="your-token",
        ),
    ],
    default_provider="feishu-main",
)
```

## Feishu Provider

The Feishu provider sends messages via Feishu webhook API.

### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `webhook_url` | string | Yes | Feishu webhook URL |
| `secret` | string | No | HMAC-SHA256 signing secret |
| `headers` | dict | No | Additional HTTP headers |
| `timeout` | float | No | Request timeout (default: 10.0) |

### Message Types

#### Text Message

```python
from feishu_webhook_bot.core.provider import Message, MessageType

message = Message(
    type=MessageType.TEXT,
    content={"text": "Hello, Feishu!"},
)
result = provider.send_message(message, target="")
```

#### Rich Text Message

```python
message = Message(
    type=MessageType.RICH_TEXT,
    content={
        "title": "Message Title",
        "content": [
            [
                {"tag": "text", "text": "Hello "},
                {"tag": "a", "text": "click here", "href": "https://example.com"},
            ]
        ],
    },
)
```

#### Interactive Card

```python
from feishu_webhook_bot.core.client import CardBuilder

card = (
    CardBuilder()
    .set_header("Notification", template="blue")
    .add_markdown("**Important:** Message content")
    .add_button("View Details", url="https://example.com")
    .build()
)

message = Message(
    type=MessageType.CARD,
    content=card,
)
```

#### Image Message

```python
message = Message(
    type=MessageType.IMAGE,
    content={"image_key": "img_v2_xxxxx"},
)
```

### Webhook Signing

When a secret is configured, messages are signed using HMAC-SHA256:

```python
config = FeishuProviderConfig(
    name="signed-webhook",
    url="https://open.feishu.cn/...",
    secret="your-signing-secret",  # Enable signing
)
```

The signature is automatically added to the request payload.

## Feishu Open Platform API

For full bot functionality beyond webhooks, use the `FeishuOpenAPI` client which provides comprehensive access to Feishu Open Platform APIs.

### Features

- **Token Management**: Automatic tenant/app access token refresh
- **Message API**: Send, reply, recall messages
- **User/Chat Queries**: Get user and chat information
- **OAuth Support**: User authorization flow

### Basic Usage

```python
from feishu_webhook_bot.providers import FeishuOpenAPI, create_feishu_api

# Using context manager (recommended)
async with FeishuOpenAPI(app_id="cli_xxx", app_secret="xxx") as api:
    # Send a text message
    result = await api.send_message(
        receive_id="oc_xxx",
        receive_id_type="chat_id",
        msg_type="text",
        content={"text": "Hello!"},
    )

    if result.success:
        print(f"Sent message: {result.message_id}")

# Or use factory function
api = create_feishu_api(app_id="cli_xxx", app_secret="xxx")
await api.connect()
# ... use api ...
await api.close()
```

### Send Messages

```python
# Send to chat by chat_id
result = await api.send_message(
    receive_id="oc_xxx",
    receive_id_type="chat_id",
    msg_type="text",
    content={"text": "Hello, chat!"},
)

# Send to user by open_id
result = await api.send_message(
    receive_id="ou_xxx",
    receive_id_type="open_id",
    msg_type="text",
    content={"text": "Hello, user!"},
)

# Send rich text
result = await api.send_message(
    receive_id="oc_xxx",
    receive_id_type="chat_id",
    msg_type="post",
    content={
        "zh_cn": {
            "title": "Title",
            "content": [[{"tag": "text", "text": "Content"}]],
        }
    },
)

# Send interactive card
result = await api.send_message(
    receive_id="oc_xxx",
    receive_id_type="chat_id",
    msg_type="interactive",
    content=card_json,
)
```

### Reply to Messages

```python
# Reply to a specific message
result = await api.reply_message(
    message_id="om_xxx",
    msg_type="text",
    content={"text": "This is a reply"},
)
```

### Get Information

```python
# Get user info
user = await api.get_user_info("ou_xxx")
print(f"User: {user.get('name')}")

# Get chat info
chat = await api.get_chat_info("oc_xxx")
print(f"Chat: {chat.get('name')}")
```

### Token Management

Tokens are automatically managed and refreshed:

```python
# Get current tenant access token
token = await api.get_tenant_access_token()

# Force refresh token
token = await api.get_tenant_access_token(force_refresh=True)
```

### Error Handling

```python
from feishu_webhook_bot.providers import FeishuAPIError

try:
    result = await api.send_message(...)
except FeishuAPIError as e:
    print(f"API Error {e.code}: {e.msg}")
    print(f"Log ID: {e.log_id}")
```

### Receive ID Types

| Type | Description | Example |
|------|-------------|---------|
| `open_id` | User's open_id | `ou_xxx` |
| `user_id` | User's user_id | `xxx` |
| `union_id` | User's union_id | `on_xxx` |
| `email` | User's email | `user@example.com` |
| `chat_id` | Chat/group ID | `oc_xxx` |

## QQ/Napcat Provider

The Napcat provider sends messages via OneBot11 HTTP API.

### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `http_url` | string | Yes | Napcat HTTP API base URL |
| `access_token` | string | No | API access token |
| `default_target` | string | No | Default message target |
| `timeout` | float | No | Request timeout (default: 10.0) |

### Target Format

Messages require a target specifying the recipient:

- **Private Message**: `private:QQ号` (e.g., `private:123456789`)
- **Group Message**: `group:群号` (e.g., `group:987654321`)

### Message Types

#### Text Message

```python
message = Message(
    type=MessageType.TEXT,
    content={"text": "Hello, QQ!"},
)
result = provider.send_message(message, target="group:123456789")
```

#### Image Message

```python
# Using URL
message = Message(
    type=MessageType.IMAGE,
    content={"url": "https://example.com/image.png"},
)

# Using base64
message = Message(
    type=MessageType.IMAGE,
    content={"base64": "iVBORw0KGgo..."},
)

# Using local file
message = Message(
    type=MessageType.IMAGE,
    content={"file": "file:///path/to/image.png"},
)
```

### CQ Code Support

Rich text is converted to CQ code format:

```python
message = Message(
    type=MessageType.RICH_TEXT,
    content={
        "content": [
            [
                {"tag": "text", "text": "Hello "},
                {"tag": "at", "user_id": "123456789"},
            ]
        ],
    },
)
# Converted to: "Hello [CQ:at,qq=123456789]"
```

### Limitations

- Interactive cards are not supported (OneBot11 limitation)
- Some rich text features may not be available

## QQ Event Handler

The `QQEventHandler` parses incoming OneBot11 events and converts them to unified `IncomingMessage` format.

### Basic Usage

```python
from feishu_webhook_bot.providers import QQEventHandler, create_qq_event_handler

# Create handler
handler = QQEventHandler(bot_qq="123456789")
# Or use factory
handler = create_qq_event_handler(bot_qq="123456789")

# Handle incoming event from Napcat webhook
message = await handler.handle_event(event_payload)
if message:
    # Process as chat message
    response = await ai_agent.chat(user_key, message.content)
    await provider.send_reply(message, response)
```

### Supported Events

| Event Type | Description | Returns |
|------------|-------------|---------|
| `message` | Private/group messages | `IncomingMessage` |
| `notice` | Group member changes, etc. | `None` (logged) |
| `request` | Friend/group requests | `None` (logged) |
| `meta_event` | Heartbeat, lifecycle | `None` (ignored) |

### Event Metadata

```python
from feishu_webhook_bot.providers import QQEventMeta

# Parse event metadata
meta = handler.parse_event_meta(payload)

print(f"Post type: {meta.post_type}")
print(f"Message type: {meta.message_type}")
print(f"Sub type: {meta.sub_type}")
print(f"Self ID: {meta.self_id}")
print(f"Time: {meta.time}")
```

### CQ Code Parsing

The handler automatically parses CQ codes:

```python
# Input: "Hello [CQ:at,qq=123456] world"
# Extracted text: "Hello  world"
# Extracted mentions: ["123456"]

# Input: [{"type": "text", "data": {"text": "Hello "}}, {"type": "at", "data": {"qq": "123456"}}]
# Extracted text: "Hello "
# Extracted mentions: ["123456"]
```

### Bot Mention Detection

```python
handler = QQEventHandler(bot_qq="123456789")

# Automatically detects @bot mentions
message = await handler.handle_event(payload)
if message.is_at_bot:
    # Bot was @mentioned
    await process_bot_command(message)
```

### Integration with ChatController

```python
from feishu_webhook_bot.chat import ChatController
from feishu_webhook_bot.providers import QQEventHandler, NapcatProvider

# Create components
handler = QQEventHandler(bot_qq="123456789")
provider = NapcatProvider(config)
controller = ChatController(
    ai_agent=ai_agent,
    providers={"qq": provider},
)

# In your webhook endpoint
async def handle_qq_webhook(payload: dict):
    message = await handler.handle_event(payload)
    if message:
        await controller.handle_incoming(message)
```

## Custom Providers

Create custom providers by extending `BaseProvider`:

```python
from feishu_webhook_bot.core.provider import (
    BaseProvider,
    Message,
    MessageType,
    ProviderConfig,
    SendResult,
)

class CustomProviderConfig(ProviderConfig):
    """Configuration for custom provider."""
    provider_type: str = "custom"
    api_url: str
    api_key: str

class CustomProvider(BaseProvider):
    """Custom message provider implementation."""

    def __init__(self, config: CustomProviderConfig):
        super().__init__(config)
        self.config = config
        self._client = None

    def connect(self) -> None:
        """Initialize connection."""
        import httpx
        self._client = httpx.Client(
            base_url=self.config.api_url,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
        )
        self._connected = True

    def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            self._client.close()
        self._connected = False

    def send_message(self, message: Message, target: str) -> SendResult:
        """Send a message."""
        if not self._connected:
            self.connect()

        try:
            payload = self._build_payload(message, target)
            response = self._client.post("/send", json=payload)
            response.raise_for_status()

            return SendResult(
                success=True,
                message_id=response.json().get("id"),
                provider=self.config.name,
            )
        except Exception as e:
            return SendResult(
                success=False,
                error=str(e),
                provider=self.config.name,
            )

    def _build_payload(self, message: Message, target: str) -> dict:
        """Build API payload from message."""
        return {
            "target": target,
            "type": message.type.value,
            "content": message.content,
        }
```

### Registering Custom Providers

```python
from feishu_webhook_bot.core.provider import ProviderRegistry

# Create registry
registry = ProviderRegistry()

# Register custom provider
custom_config = CustomProviderConfig(
    name="my-custom",
    api_url="https://api.example.com",
    api_key="secret-key",
)
custom_provider = CustomProvider(custom_config)
registry.register("my-custom", custom_provider)

# Use provider
provider = registry.get("my-custom")
result = provider.send_message(message, target="user123")
```

## Provider Registry

The `ProviderRegistry` manages multiple provider instances:

```python
from feishu_webhook_bot.core.provider import ProviderRegistry

registry = ProviderRegistry()

# Register providers
registry.register("feishu", feishu_provider)
registry.register("qq", napcat_provider)

# Get provider by name
provider = registry.get("feishu")

# Get default provider
default = registry.get_default()

# List all providers
all_providers = registry.list_all()

# Check if provider exists
if registry.has("feishu"):
    provider = registry.get("feishu")

# Remove provider
registry.unregister("old-provider")
```

### Using with FeishuBot

```python
from feishu_webhook_bot import FeishuBot

bot = FeishuBot.from_config("config.yaml")

# Access providers
feishu = bot.providers.get("feishu-main")
qq = bot.providers.get("qq-group")

# Send via specific provider
result = feishu.send_message(message, target="")
result = qq.send_message(message, target="group:123456")

# Send via default provider
result = bot.default_provider.send_message(message, target="")
```

## Best Practices

### 1. Use Environment Variables

Store sensitive credentials in environment variables:

```yaml
providers:
  - provider_type: "feishu"
    webhook_url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_SECRET}"
```

### 2. Configure Circuit Breakers

Enable circuit breakers to handle provider failures:

```yaml
providers:
  - provider_type: "feishu"
    circuit_breaker:
      failure_threshold: 5
      reset_timeout: 30.0
      half_open_max_calls: 3
```

### 3. Enable Message Tracking

Track message delivery for important messages:

```yaml
providers:
  - provider_type: "feishu"
    message_tracking: true

message_tracking:
  enabled: true
  db_path: "data/messages.db"
```

### 4. Set Appropriate Timeouts

Configure timeouts based on provider response times:

```yaml
providers:
  - provider_type: "feishu"
    timeout: 10.0  # Feishu is usually fast

  - provider_type: "napcat"
    timeout: 30.0  # Local service may need more time
```

### 5. Handle Provider Failures

Always check `SendResult` for errors:

```python
result = provider.send_message(message, target)
if not result.success:
    logger.error(f"Failed to send: {result.error}")
    # Implement fallback logic
```

### 6. Use Default Provider

Set a default provider for convenience:

```yaml
default_provider: "feishu-main"
```

```python
# Uses default provider
bot.send_text("Hello!")
```

## Troubleshooting

### Feishu Provider Issues

**Problem**: Messages not sending

**Solutions**:

1. Verify webhook URL is correct
2. Check if bot is still in the group
3. Verify signing secret matches
4. Check network connectivity

### Napcat Provider Issues

**Problem**: Connection refused

**Solutions**:

1. Verify Napcat is running
2. Check HTTP URL and port
3. Verify access token if configured
4. Check firewall settings

### Circuit Breaker Open

**Problem**: Provider circuit breaker is open

**Solutions**:

1. Check provider service status
2. Wait for reset timeout
3. Reduce failure threshold if too sensitive
4. Check logs for failure reasons

## See Also

- [Core Reference](../reference/core-reference.md) - Circuit breaker and message tracking
- [API Reference](../reference/api.md) - Complete API documentation
- [YAML Configuration](yaml-configuration-guide.md) - Configuration reference
