# Event Handling Guide

Complete guide to handling Feishu events and webhooks in the bot framework.

## Table of Contents

- [Overview](#overview)
- [Event Server Setup](#event-server-setup)
- [Event Types](#event-types)
- [Event Handlers](#event-handlers)
- [Message Events](#message-events)
- [Card Callbacks](#card-callbacks)
- [Event Filtering](#event-filtering)
- [Error Handling](#error-handling)
- [Testing Events](#testing-events)

## Overview

The event handling system allows your bot to receive and respond to events from Feishu, including:

- Incoming messages
- Card button clicks
- User mentions
- Group events
- Custom events

### Architecture

```text
Feishu Platform → Event Server → Event Router → Event Handlers
                                      ↓
                              Event Filters
                                      ↓
                              Your Code
```

## Event Server Setup

### Configuration

```yaml
# config.yaml
event_server:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  path: "/webhook"
  verification_token: "${FEISHU_VERIFICATION_TOKEN}"
  encrypt_key: "${FEISHU_ENCRYPT_KEY}"
```

### Starting the Server

```python
from feishu_webhook_bot import FeishuBot

bot = FeishuBot.from_config("config.yaml")

# Start bot with event server
bot.start()  # Starts scheduler, plugins, and event server
```

### Manual Server Control

```python
# Start event server separately
await bot.event_server.start()

# Stop event server
await bot.event_server.stop()
```

### URL Configuration in Feishu

1. Go to Feishu Open Platform
2. Navigate to your app's Event Subscriptions
3. Set Request URL: `https://your-domain.com/webhook`
4. Verify the endpoint

## Event Types

### Message Events

| Event | Description |
|-------|-------------|
| `im.message.receive_v1` | New message received |
| `im.message.message_read_v1` | Message read |
| `im.message.recalled_v1` | Message recalled |

### Chat Events

| Event | Description |
|-------|-------------|
| `im.chat.member.user.added_v1` | User added to chat |
| `im.chat.member.user.deleted_v1` | User removed from chat |
| `im.chat.disbanded_v1` | Chat disbanded |

### Card Events

| Event | Description |
|-------|-------------|
| `card.action.trigger` | Card button clicked |

### Bot Events

| Event | Description |
|-------|-------------|
| `im.chat.member.bot.added_v1` | Bot added to chat |
| `im.chat.member.bot.deleted_v1` | Bot removed from chat |

## Event Handlers

### Registering Handlers

```python
from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core.event_server import Event

bot = FeishuBot.from_config("config.yaml")

# Register handler for specific event type
@bot.on_event("im.message.receive_v1")
async def handle_message(event: Event):
    message = event.data.get("message", {})
    content = message.get("content", "")
    print(f"Received message: {content}")

# Register handler for multiple event types
@bot.on_event(["im.chat.member.user.added_v1", "im.chat.member.user.deleted_v1"])
async def handle_member_change(event: Event):
    print(f"Member change: {event.type}")
```

### Handler in Plugin

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class EchoPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="echo", version="1.0.0")

    def on_enable(self) -> None:
        self.register_event_handler("im.message.receive_v1", self.handle_message)

    async def handle_message(self, event: dict) -> None:
        message = event.get("message", {})
        chat_id = message.get("chat_id")
        content = message.get("content", "")

        # Echo the message back
        self.client.send_text(f"You said: {content}", chat_id=chat_id)
```

### Async Handlers

```python
@bot.on_event("im.message.receive_v1")
async def async_handler(event: Event):
    # Async operations
    result = await fetch_data()
    await process_message(event, result)
```

### Sync Handlers

```python
@bot.on_event("im.message.receive_v1")
def sync_handler(event: Event):
    # Sync operations (will be run in thread pool)
    process_message(event)
```

## Message Events

### Handling Incoming Messages

```python
@bot.on_event("im.message.receive_v1")
async def handle_message(event: Event):
    message = event.data.get("message", {})

    # Extract message details
    message_id = message.get("message_id")
    chat_id = message.get("chat_id")
    chat_type = message.get("chat_type")  # "p2p" or "group"
    message_type = message.get("message_type")  # "text", "image", etc.
    content = message.get("content")

    # Get sender info
    sender = event.data.get("sender", {})
    sender_id = sender.get("sender_id", {}).get("user_id")

    # Process based on message type
    if message_type == "text":
        text_content = json.loads(content).get("text", "")
        await process_text_message(chat_id, text_content)
    elif message_type == "image":
        image_key = json.loads(content).get("image_key")
        await process_image_message(chat_id, image_key)
```

### Message Content Parsing

```python
import json

def parse_message_content(message: dict) -> dict:
    """Parse message content based on type."""
    message_type = message.get("message_type")
    content = message.get("content", "{}")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"raw": content}

    return {
        "type": message_type,
        "content": parsed,
        "text": parsed.get("text", "") if message_type == "text" else None,
        "image_key": parsed.get("image_key") if message_type == "image" else None,
    }
```

### Mention Detection

```python
@bot.on_event("im.message.receive_v1")
async def handle_mention(event: Event):
    message = event.data.get("message", {})
    mentions = message.get("mentions", [])

    # Check if bot was mentioned
    bot_mentioned = any(
        m.get("id", {}).get("user_id") == bot.bot_id
        for m in mentions
    )

    if bot_mentioned:
        await respond_to_mention(event)
```

## Card Callbacks

### Handling Button Clicks

```python
@bot.on_event("card.action.trigger")
async def handle_card_action(event: Event):
    action = event.data.get("action", {})

    # Get action details
    action_tag = action.get("tag")  # "button", "select", etc.
    action_value = action.get("value", {})

    # Get context
    open_id = event.data.get("open_id")
    open_message_id = event.data.get("open_message_id")

    # Handle based on action
    if action_value.get("action") == "approve":
        await handle_approval(action_value.get("request_id"))
    elif action_value.get("action") == "reject":
        await handle_rejection(action_value.get("request_id"))
```

### Card with Callbacks

```python
from feishu_webhook_bot.core.client import CardBuilder

# Create card with callback buttons
card = (
    CardBuilder()
    .set_header("Approval Request")
    .add_markdown("Please review this request.")
    .add_button(
        "Approve",
        callback="card_callback",
        value={"action": "approve", "request_id": "123"}
    )
    .add_button(
        "Reject",
        callback="card_callback",
        value={"action": "reject", "request_id": "123"},
        style="danger"
    )
    .build()
)

bot.send_card(card)
```

### Updating Cards

```python
@bot.on_event("card.action.trigger")
async def handle_and_update(event: Event):
    action_value = event.data.get("action", {}).get("value", {})
    message_id = event.data.get("open_message_id")

    if action_value.get("action") == "approve":
        # Update the card to show approved status
        updated_card = (
            CardBuilder()
            .set_header("✅ Approved", template="green")
            .add_markdown("This request has been approved.")
            .build()
        )

        await bot.update_card(message_id, updated_card)
```

## Event Filtering

### Filter by Event Type

```python
from feishu_webhook_bot.core.event_server import EventFilter

# Only handle text messages
@bot.on_event("im.message.receive_v1")
@EventFilter.message_type("text")
async def handle_text_only(event: Event):
    pass
```

### Filter by Chat Type

```python
# Only handle group messages
@bot.on_event("im.message.receive_v1")
@EventFilter.chat_type("group")
async def handle_group_only(event: Event):
    pass

# Only handle direct messages
@bot.on_event("im.message.receive_v1")
@EventFilter.chat_type("p2p")
async def handle_dm_only(event: Event):
    pass
```

### Custom Filters

```python
def is_admin_user(event: Event) -> bool:
    """Check if sender is an admin."""
    sender_id = event.data.get("sender", {}).get("sender_id", {}).get("user_id")
    return sender_id in ADMIN_USER_IDS

@bot.on_event("im.message.receive_v1")
async def handle_admin_command(event: Event):
    if not is_admin_user(event):
        return  # Ignore non-admin users

    # Process admin command
    await process_admin_command(event)
```

### Filter Chain

```python
class EventFilters:
    @staticmethod
    def require_mention(event: Event) -> bool:
        mentions = event.data.get("message", {}).get("mentions", [])
        return len(mentions) > 0

    @staticmethod
    def require_text(event: Event) -> bool:
        message_type = event.data.get("message", {}).get("message_type")
        return message_type == "text"

@bot.on_event("im.message.receive_v1")
async def handle_mention_text(event: Event):
    if not EventFilters.require_mention(event):
        return
    if not EventFilters.require_text(event):
        return

    # Handle text message with mention
    await process_mention(event)
```

## Error Handling

### Handler-Level Error Handling

```python
@bot.on_event("im.message.receive_v1")
async def handle_with_error_handling(event: Event):
    try:
        await process_message(event)
    except ValueError as e:
        logger.warning(f"Invalid message: {e}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Optionally notify about the error
        await notify_error(event, e)
```

### Global Error Handler

```python
@bot.on_event_error
async def global_error_handler(event: Event, error: Exception):
    logger.error(f"Event handling error: {error}", exc_info=True)

    # Send error notification
    bot.send_text(
        f"⚠️ Error processing event: {type(error).__name__}",
        webhook="alerts"
    )
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@bot.on_event("im.message.receive_v1")
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def handle_with_retry(event: Event):
    await process_message(event)
```

## Testing Events

### Mock Events

```python
import pytest
from feishu_webhook_bot.core.event_server import Event

def create_mock_message_event(text: str, chat_id: str = "test_chat") -> Event:
    return Event(
        type="im.message.receive_v1",
        data={
            "message": {
                "message_id": "test_msg_id",
                "chat_id": chat_id,
                "chat_type": "group",
                "message_type": "text",
                "content": json.dumps({"text": text}),
            },
            "sender": {
                "sender_id": {"user_id": "test_user"}
            }
        }
    )

@pytest.mark.asyncio
async def test_message_handler():
    event = create_mock_message_event("Hello")
    await handle_message(event)
```

### Integration Testing

```python
import httpx
import pytest

@pytest.mark.asyncio
async def test_webhook_endpoint():
    async with httpx.AsyncClient() as client:
        # Test verification challenge
        response = await client.post(
            "http://localhost:8080/webhook",
            json={
                "challenge": "test_challenge",
                "type": "url_verification"
            }
        )
        assert response.status_code == 200
        assert response.json()["challenge"] == "test_challenge"
```

### Event Simulation

```python
async def simulate_message_event(bot: FeishuBot, text: str):
    """Simulate a message event for testing."""
    event = {
        "schema": "2.0",
        "header": {
            "event_type": "im.message.receive_v1",
            "event_id": "test_event_id",
        },
        "event": {
            "message": {
                "message_id": "test_msg",
                "chat_id": "test_chat",
                "message_type": "text",
                "content": json.dumps({"text": text}),
            }
        }
    }

    await bot.event_server.handle_event(event)
```

## Best Practices

### Handler Organization

```python
# handlers/messages.py
async def handle_text_message(event: Event):
    pass

async def handle_image_message(event: Event):
    pass

# handlers/cards.py
async def handle_approval_action(event: Event):
    pass

# main.py
bot.on_event("im.message.receive_v1")(handle_text_message)
bot.on_event("card.action.trigger")(handle_approval_action)
```

### Idempotency

```python
from functools import lru_cache

processed_events = set()

@bot.on_event("im.message.receive_v1")
async def idempotent_handler(event: Event):
    event_id = event.data.get("event_id")

    if event_id in processed_events:
        return  # Already processed

    processed_events.add(event_id)
    await process_message(event)
```

### Response Time

```python
import asyncio

@bot.on_event("im.message.receive_v1")
async def fast_response_handler(event: Event):
    # Acknowledge quickly
    asyncio.create_task(process_in_background(event))

    # Return immediately
    return {"status": "accepted"}

async def process_in_background(event: Event):
    # Heavy processing here
    await heavy_operation(event)
```

## See Also

- [Automation Guide](automation-guide.md) - Event-triggered automation
- [Plugin Development](plugin-guide.md) - Event handling in plugins
- [API Reference](../reference/api.md) - Event server API
