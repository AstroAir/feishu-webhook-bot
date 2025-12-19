# Chat Controller Guide

Complete guide to the unified chat controller for multi-platform message handling.

## Table of Contents

- [Overview](#overview)
- [ChatController](#chatcontroller)
- [ChatConfig](#chatconfig)
- [ChatContext](#chatcontext)
- [Middleware System](#middleware-system)
- [Message Routing](#message-routing)
- [Broadcasting](#broadcasting)
- [Integration Examples](#integration-examples)
- [Best Practices](#best-practices)

## Overview

The chat controller module (`feishu_webhook_bot.chat`) provides a unified orchestrator for routing messages from multiple platforms (Feishu, QQ, etc.) to appropriate handlers and sending responses.

### Key Features

- **Multi-platform routing**: Route messages from Feishu, QQ, and custom platforms
- **Command integration**: Built-in support for slash commands (`/help`, `/reset`, etc.)
- **AI conversation**: Seamless AI agent integration with context preservation
- **Middleware pipeline**: Extensible message processing with custom middleware
- **Configurable behavior**: Per-chat-type settings (private, group)
- **Error handling**: Graceful degradation and error responses

### Architecture

```text
Incoming Message → ChatController
                        ↓
                   Middleware Pipeline
                        ↓
                   Chat Type Check
                        ↓
              ┌─────────┴─────────┐
              ↓                   ↓
        Command Handler      AI Agent
              ↓                   ↓
              └─────────┬─────────┘
                        ↓
                   Send Reply
                        ↓
                   Provider
```

## ChatController

The main orchestrator class for handling incoming messages.

### Basic Usage

```python
from feishu_webhook_bot.chat import ChatController, ChatConfig
from feishu_webhook_bot.core.message_handler import IncomingMessage

# Create controller with AI agent
controller = ChatController(
    ai_agent=ai_agent,
    command_handler=command_handler,
    providers={"feishu": feishu_provider, "qq": qq_provider},
    config=ChatConfig(require_at_in_groups=True),
)

# Handle incoming message
msg = IncomingMessage(
    id="msg_123",
    platform="feishu",
    chat_type="private",
    chat_id="",
    sender_id="user_123",
    sender_name="Alice",
    content="Hello!",
)
await controller.handle_incoming(msg)
```

### Factory Function

Use `create_chat_controller()` for quick setup with integrated command handler:

```python
from feishu_webhook_bot.chat import create_chat_controller, ChatConfig
from feishu_webhook_bot.ai import AIAgent

# Create AI agent
ai_agent = AIAgent(model="gpt-4o")

# Create chat controller with command handler
controller = create_chat_controller(
    ai_agent=ai_agent,
    providers={"feishu": feishu_provider},
    config=ChatConfig(max_message_length=2000),
    available_models=["gpt-4o", "claude-3-sonnet"],
)

# Controller now has integrated /help, /reset, /model, etc. commands
```

### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `ai_agent` | `AIAgent \| None` | AI agent for conversation handling |
| `command_handler` | `CommandHandler \| None` | Handler for slash commands |
| `providers` | `dict[str, BaseProvider]` | Platform providers `{platform: provider}` |
| `config` | `ChatConfig \| None` | Chat configuration |
| `conversation_store` | `PersistentConversationManager \| None` | Persistent conversation storage |

### Methods

#### `handle_incoming(message: IncomingMessage) -> None`

Main entry point for handling incoming messages.

```python
await controller.handle_incoming(message)
```

#### `send_reply(original, reply, reply_in_thread=True) -> SendResult | None`

Send reply to the original message.

```python
result = await controller.send_reply(
    original=message,
    reply="Hello back!",
    reply_in_thread=True,
)
if result and result.success:
    print(f"Reply sent: {result.message_id}")
```

#### `broadcast(message, platforms=None, targets=None) -> dict[str, list[SendResult]]`

Broadcast message to multiple platforms and targets.

```python
results = await controller.broadcast(
    "System announcement",
    platforms=["feishu", "qq"],
    targets={
        "feishu": ["webhook_url"],
        "qq": ["group:123", "private:456"]
    }
)

for platform, send_results in results.items():
    for result in send_results:
        if result.success:
            print(f"Sent to {platform}: {result.message_id}")
```

#### `add_provider(name, provider) -> None`

Add or replace a message provider.

```python
controller.add_provider("telegram", telegram_provider)
```

#### `get_provider(platform) -> BaseProvider | None`

Get provider for a platform.

```python
provider = controller.get_provider("feishu")
```

#### `get_stats() -> dict[str, Any]`

Get controller statistics.

```python
stats = await controller.get_stats()
# {
#   "providers": ["feishu", "qq"],
#   "middleware_count": 3,
#   "config": {...}
# }
```

## ChatConfig

Configuration for chat controller behavior.

### Configuration Options

```python
from feishu_webhook_bot.chat import ChatConfig

config = ChatConfig(
    enabled=True,                    # Enable chat functionality
    enable_in_groups=True,           # Enable in group chats
    require_at_in_groups=True,       # Require @bot in groups to respond
    enable_private=True,             # Enable private chats
    command_prefix="/",              # Prefix for commands
    max_message_length=4000,         # Maximum response message length
    typing_indicator=False,          # Send typing indicator while processing
    error_message="抱歉，处理您的消息时出现了问题，请稍后重试。",
)
```

### Configuration Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable chat functionality entirely |
| `enable_in_groups` | `bool` | `True` | Enable response to group chat messages |
| `require_at_in_groups` | `bool` | `True` | Require @bot mention in group chats |
| `enable_private` | `bool` | `True` | Enable response to private messages |
| `command_prefix` | `str` | `"/"` | Prefix character for commands |
| `max_message_length` | `int` | `4000` | Maximum length for response messages |
| `typing_indicator` | `bool` | `False` | Send typing indicator while processing |
| `error_message` | `str` | (Chinese) | Default error message on failures |

### YAML Configuration

```yaml
chat:
  enabled: true
  enable_in_groups: true
  require_at_in_groups: true
  enable_private: true
  command_prefix: "/"
  max_message_length: 4000
  typing_indicator: false
  error_message: "Sorry, an error occurred. Please try again."
```

## ChatContext

Runtime context for a chat interaction, passed through the middleware pipeline.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `IncomingMessage` | The incoming message being processed |
| `user_key` | `str` | Unique user identifier (`platform:chat_type:sender_id`) |
| `provider` | `BaseProvider \| None` | Message provider for the source platform |
| `ai_agent` | `AIAgent \| None` | AI agent for conversation |
| `metadata` | `dict[str, Any]` | Additional runtime metadata for handlers |

### Usage in Middleware

```python
from feishu_webhook_bot.chat import ChatContext

@controller.middleware
async def log_context(ctx: ChatContext) -> bool:
    print(f"User: {ctx.user_key}")
    print(f"Platform: {ctx.message.platform}")
    print(f"Content: {ctx.message.content}")
    return True  # Continue processing
```

## Middleware System

The middleware system allows you to intercept and process messages before they reach command handlers or AI.

### Registering Middleware

```python
@controller.middleware
async def my_middleware(ctx: ChatContext) -> bool:
    # Process the message
    # Return True to continue, False to stop
    return True
```

### Middleware Examples

#### Logging Middleware

```python
@controller.middleware
async def log_messages(ctx: ChatContext) -> bool:
    logger.info(
        "Message from %s: %s",
        ctx.user_key,
        ctx.message.content[:100]
    )
    return True
```

#### Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta

rate_limits = defaultdict(list)
RATE_LIMIT = 10  # messages per minute

@controller.middleware
async def rate_limit(ctx: ChatContext) -> bool:
    now = datetime.now()
    user_key = ctx.user_key

    # Clean old entries
    rate_limits[user_key] = [
        t for t in rate_limits[user_key]
        if now - t < timedelta(minutes=1)
    ]

    if len(rate_limits[user_key]) >= RATE_LIMIT:
        await controller.send_reply(
            ctx.message,
            "请稍后再试，您发送消息过于频繁。"
        )
        return False  # Stop processing

    rate_limits[user_key].append(now)
    return True
```

#### Content Filtering

```python
BLOCKED_WORDS = ["spam", "advertisement"]

@controller.middleware
async def content_filter(ctx: ChatContext) -> bool:
    content = ctx.message.content.lower()

    for word in BLOCKED_WORDS:
        if word in content:
            logger.warning("Blocked message from %s: contains '%s'", ctx.user_key, word)
            return False

    return True
```

#### User Authentication

```python
ALLOWED_USERS = {"user_123", "user_456"}

@controller.middleware
async def auth_check(ctx: ChatContext) -> bool:
    if ctx.message.sender_id not in ALLOWED_USERS:
        await controller.send_reply(
            ctx.message,
            "抱歉，您没有使用此机器人的权限。"
        )
        return False
    return True
```

### Middleware Execution Order

Middleware is executed in registration order. If any middleware returns `False`, subsequent middleware and message processing are skipped.

```python
# Executed in order: 1 → 2 → 3
@controller.middleware
async def middleware_1(ctx): return True

@controller.middleware
async def middleware_2(ctx): return True

@controller.middleware
async def middleware_3(ctx): return True
```

## Message Routing

The controller routes messages based on configuration and content.

### Routing Flow

1. **Check if chat is enabled** (`config.enabled`)
2. **Check chat type settings** (`enable_in_groups`, `enable_private`)
3. **Check @bot requirement** for groups (`require_at_in_groups`)
4. **Run middleware pipeline**
5. **Check for commands** (starts with `command_prefix`)
6. **Process with AI agent** (if no command matched)

### Command Processing

Commands are processed before AI conversation:

```python
# If message starts with command prefix
if content.startswith(config.command_prefix):
    is_cmd, result = await command_handler.process(message)
    if is_cmd and result:
        await send_reply(message, result.response)
        return  # Don't process with AI
```

### AI Processing

If the message is not a command, it's sent to the AI agent:

```python
response = await ai_agent.chat(user_key, content)
if response:
    # Truncate if too long
    if len(response) > config.max_message_length:
        response = response[:config.max_message_length - 3] + "..."
    await send_reply(message, response)
```

## Broadcasting

Send messages to multiple platforms and targets simultaneously.

### Basic Broadcast

```python
# Broadcast to all registered providers
results = await controller.broadcast("Hello everyone!")
```

### Targeted Broadcast

```python
# Broadcast to specific platforms
results = await controller.broadcast(
    "Platform-specific message",
    platforms=["feishu", "qq"],
)
```

### Multi-Target Broadcast

```python
# Broadcast to specific targets on each platform
results = await controller.broadcast(
    "Targeted announcement",
    platforms=["feishu", "qq"],
    targets={
        "feishu": ["webhook_1", "webhook_2"],
        "qq": ["group:123456", "group:789012"]
    }
)
```

### Handling Broadcast Results

```python
results = await controller.broadcast("Test message")

for platform, send_results in results.items():
    success_count = sum(1 for r in send_results if r.success)
    fail_count = len(send_results) - success_count

    print(f"{platform}: {success_count} sent, {fail_count} failed")

    for result in send_results:
        if not result.success:
            logger.error(f"Failed to send to {platform}: {result.error}")
```

## Integration Examples

### Full Bot Setup

```python
from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.chat import create_chat_controller, ChatConfig
from feishu_webhook_bot.ai import AIAgent, AIConfig
from feishu_webhook_bot.providers import FeishuProvider, NapcatProvider

# Create AI agent
ai_config = AIConfig(enabled=True, model="openai:gpt-4o")
ai_agent = AIAgent(ai_config)

# Create providers
feishu_provider = FeishuProvider(config=feishu_config)
qq_provider = NapcatProvider(config=napcat_config)

# Create chat controller
chat_config = ChatConfig(
    require_at_in_groups=True,
    max_message_length=2000,
)

controller = create_chat_controller(
    ai_agent=ai_agent,
    providers={
        "feishu": feishu_provider,
        "qq": qq_provider,
    },
    config=chat_config,
    available_models=["gpt-4o", "gpt-4o-mini", "claude-3-sonnet"],
)

# Add middleware
@controller.middleware
async def log_all(ctx):
    logger.info("Message: %s", ctx.message.content)
    return True

# Start processing
await ai_agent.start()
```

### Event Server Integration

```python
from feishu_webhook_bot.core.message_parsers import FeishuMessageParser

# Create parser
parser = FeishuMessageParser(bot_open_id="ou_bot_xxx")

# In event handler
@bot.on_event("im.message.receive_v1")
async def handle_message(event):
    # Parse to IncomingMessage
    message = parser.parse(event.data)
    if message:
        await controller.handle_incoming(message)
```

### Plugin Integration

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class ChatPlugin(BasePlugin):
    def __init__(self, controller: ChatController):
        self.controller = controller

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="chat-plugin", version="1.0.0")

    def on_enable(self) -> None:
        # Register custom middleware
        @self.controller.middleware
        async def plugin_middleware(ctx):
            # Plugin-specific processing
            return True
```

## Best Practices

### 1. Configure Appropriate Limits

```python
config = ChatConfig(
    max_message_length=2000,  # Prevent overly long responses
    require_at_in_groups=True,  # Reduce noise in groups
)
```

### 2. Use Middleware for Cross-Cutting Concerns

```python
# Good: Logging, rate limiting, auth in middleware
@controller.middleware
async def combined_middleware(ctx):
    log_message(ctx)
    if not check_rate_limit(ctx):
        return False
    if not check_auth(ctx):
        return False
    return True
```

### 3. Handle Errors Gracefully

```python
config = ChatConfig(
    error_message="抱歉，处理消息时出错了。请稍后重试或联系管理员。"
)
```

### 4. Monitor Controller Stats

```python
# Periodically check stats
stats = await controller.get_stats()
logger.info("Controller stats: %s", stats)
```

### 5. Use Factory Function for Standard Setup

```python
# Recommended: Use factory function
controller = create_chat_controller(
    ai_agent=ai_agent,
    providers=providers,
    config=config,
)

# Instead of manual setup
# controller = ChatController(...)
# command_handler = CommandHandler(...)
```

## See Also

- [Message Types](message-types.md) - Message format reference
- [Event Handling](event-handling.md) - Feishu event handling
- [Providers Guide](providers-guide.md) - Multi-provider setup
- [AI Multi-Provider](../ai/multi-provider.md) - AI agent configuration
- [Core Reference](../reference/core-reference.md) - Core components
