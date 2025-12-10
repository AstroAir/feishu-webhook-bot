# Conversation Store Guide

Complete guide to persistent conversation storage using SQLAlchemy.

## Table of Contents

- [Overview](#overview)
- [Database Models](#database-models)
- [PersistentConversationManager](#persistentconversationmanager)
- [CRUD Operations](#crud-operations)
- [Analytics and Export](#analytics-and-export)
- [Maintenance](#maintenance)
- [Configuration](#configuration)
- [Best Practices](#best-practices)

## Overview

The conversation store module (`feishu_webhook_bot.ai.conversation_store`) provides database-backed persistence for AI conversations. It uses SQLAlchemy for ORM and supports SQLite by default.

### Key Features

- **Persistent storage**: Conversations survive restarts
- **Token tracking**: Track input/output tokens per conversation
- **Message history**: Store and retrieve conversation messages
- **Analytics**: Get statistics about conversations
- **Export/Import**: Backup and restore conversations
- **Automatic cleanup**: Remove old conversations

### Architecture

```text
PersistentConversationManager
           ↓
    SQLAlchemy ORM
           ↓
┌──────────────────────┐
│   ConversationRecord │
│   ├── id             │
│   ├── user_key       │
│   ├── platform       │
│   ├── messages[]     │
│   └── stats          │
└──────────────────────┘
           ↓
┌──────────────────────┐
│    MessageRecord     │
│   ├── id             │
│   ├── role           │
│   ├── content        │
│   └── tokens         │
└──────────────────────┘
```

## Database Models

### ConversationRecord

Represents a conversation session with a user.

| Column          | Type          | Description                                             |
| --------------- | ------------- | ------------------------------------------------------- |
| `id`            | `Integer`     | Primary key                                             |
| `user_key`      | `String(255)` | Unique user identifier (`platform:chat_type:sender_id`) |
| `platform`      | `String(50)`  | Platform name (feishu, qq, etc.)                        |
| `chat_id`       | `String(255)` | Chat or group ID                                        |
| `created_at`    | `DateTime`    | Conversation creation timestamp                         |
| `last_activity` | `DateTime`    | Last activity timestamp                                 |
| `summary`       | `Text`        | Optional conversation summary                           |
| `total_tokens`  | `Integer`     | Total tokens used                                       |
| `message_count` | `Integer`     | Total message count                                     |

### MessageRecord

Represents an individual message in a conversation.

| Column            | Type         | Description                                  |
| ----------------- | ------------ | -------------------------------------------- |
| `id`              | `Integer`    | Primary key                                  |
| `conversation_id` | `Integer`    | Foreign key to conversation                  |
| `role`            | `String(20)` | Message role (user, assistant, system, tool) |
| `content`         | `Text`       | Message content                              |
| `timestamp`       | `DateTime`   | Message timestamp                            |
| `tokens`          | `Integer`    | Token count for this message                 |
| `metadata_json`   | `Text`       | JSON metadata (tool calls, etc.)             |

## PersistentConversationManager

The main class for managing persistent conversations.

### Initialization

```python
from feishu_webhook_bot.ai.conversation_store import PersistentConversationManager

# Default SQLite in data directory
manager = PersistentConversationManager()

# Custom SQLite path
manager = PersistentConversationManager(
    data_dir="my_data",
)

# Custom database URL
manager = PersistentConversationManager(
    db_url="sqlite:///conversations.db",
)

# PostgreSQL
manager = PersistentConversationManager(
    db_url="postgresql://user:pass@localhost/dbname",
)

# With SQL logging
manager = PersistentConversationManager(
    db_url="sqlite:///conversations.db",
    echo=True,  # Log SQL statements
)
```

### Constructor Parameters

| Parameter  | Type          | Default  | Description                   |
| ---------- | ------------- | -------- | ----------------------------- |
| `db_url`   | `str \| None` | `None`   | SQLAlchemy database URL       |
| `echo`     | `bool`        | `False`  | Enable SQL logging            |
| `data_dir` | `str \| None` | `"data"` | Directory for SQLite database |

## CRUD Operations

### Get or Create Conversation

```python
# Get existing or create new conversation
conv = manager.get_or_create(
    user_key="feishu:group:user123",
    platform="feishu",
    chat_id="chat456",
)

print(f"Conversation ID: {conv.id}")
print(f"Created at: {conv.created_at}")
```

### Save Message

```python
# Save a user message
message = manager.save_message(
    conversation_id=conv.id,
    role="user",
    content="Hello, how are you?",
    tokens=15,
)

# Save an assistant message with metadata
message = manager.save_message(
    conversation_id=conv.id,
    role="assistant",
    content="I'm doing great! How can I help you?",
    tokens=25,
    metadata={"model": "gpt-4o", "finish_reason": "stop"},
)

# Save a tool message
message = manager.save_message(
    conversation_id=conv.id,
    role="tool",
    content='{"result": "sunny, 25°C"}',
    tokens=10,
    metadata={"tool_name": "weather", "tool_call_id": "call_123"},
)
```

### Load History

```python
# Load conversation history
history = manager.load_history(
    conversation_id=conv.id,
    max_turns=10,  # Maximum user+assistant pairs
)

for msg in history:
    print(f"{msg['role']}: {msg['content'][:50]}...")
    print(f"  Tokens: {msg['tokens']}")
    print(f"  Time: {msg['timestamp']}")
```

### Get Conversation by User

```python
# Get most recent conversation for a user
conv = manager.get_conversation_by_user("feishu:group:user123")

if conv:
    print(f"Found conversation: {conv.id}")
    print(f"Messages: {conv.message_count}")
    print(f"Tokens: {conv.total_tokens}")
else:
    print("No conversation found")
```

### Update Stats

```python
# Update token usage after AI response
manager.update_conversation_stats(
    conversation_id=conv.id,
    tokens_used=150,
)
```

### Clear Conversation

```python
# Clear messages but keep conversation record
manager.clear_conversation(conversation_id=conv.id)
```

### Delete Conversation

```python
# Delete conversation and all messages
manager.delete_conversation(conversation_id=conv.id)
```

## Analytics and Export

### Get Statistics

```python
# Get overall statistics
stats = manager.get_stats()

print(f"Total conversations: {stats['total_conversations']}")
print(f"Total messages: {stats['total_messages']}")
print(f"Total tokens: {stats['total_tokens']}")
print(f"Avg messages/conv: {stats['average_messages_per_conversation']}")
print(f"Avg tokens/conv: {stats['average_tokens_per_conversation']}")
print(f"Longest conversation: {stats['longest_conversation_messages']} messages")
print(f"Most active user: {stats['longest_conversation_user']}")
```

### Export Conversation

```python
import json

# Export conversation to dict
data = manager.export_conversation(conversation_id=conv.id)

# Save to file
with open("conversation_backup.json", "w") as f:
    json.dump(data, f, indent=2)

# Structure:
# {
#   "conversation": {
#     "id": 1,
#     "user_key": "feishu:group:user123",
#     "platform": "feishu",
#     "chat_id": "chat456",
#     "created_at": "2025-01-08T10:00:00Z",
#     "last_activity": "2025-01-08T11:30:00Z",
#     "summary": null,
#     "total_tokens": 5000,
#     "message_count": 50
#   },
#   "messages": [
#     {
#       "id": 1,
#       "role": "user",
#       "content": "Hello",
#       "timestamp": "2025-01-08T10:00:00Z",
#       "tokens": 5,
#       "metadata": {}
#     },
#     ...
#   ]
# }
```

### Import Conversation

```python
import json

# Load from file
with open("conversation_backup.json", "r") as f:
    data = json.load(f)

# Import conversation
conv = manager.import_conversation(data)

print(f"Imported conversation: {conv.id}")
print(f"User: {conv.user_key}")
```

## Maintenance

### Cleanup Old Conversations

```python
# Delete conversations older than 30 days
deleted_count = manager.cleanup_old_conversations(days=30)
print(f"Deleted {deleted_count} old conversations")

# Delete conversations older than 7 days
deleted_count = manager.cleanup_old_conversations(days=7)
```

### Scheduled Cleanup

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=3)  # Run at 3 AM daily
def cleanup_job():
    deleted = manager.cleanup_old_conversations(days=30)
    logger.info(f"Cleaned up {deleted} old conversations")

scheduler.start()
```

### Database Maintenance

```python
# For SQLite, you can vacuum the database periodically
from sqlalchemy import text

with manager.get_session() as session:
    session.execute(text("VACUUM"))
```

## Configuration

### YAML Configuration

```yaml
ai:
    conversation_persistence:
        enabled: true
        db_url: "sqlite:///data/conversations.db"
        cleanup_days: 30
        max_history_turns: 20
```

### Environment Variables

```bash
# Database URL
export CONVERSATION_DB_URL="postgresql://user:pass@localhost/conversations"

# Data directory for SQLite
export CONVERSATION_DATA_DIR="./data"
```

### Integration with AIAgent

```python
from feishu_webhook_bot.ai import AIAgent, AIConfig
from feishu_webhook_bot.ai.conversation_store import PersistentConversationManager

# Create persistent manager
store = PersistentConversationManager(
    db_url="sqlite:///data/conversations.db",
)

# Create AI config with persistence
config = AIConfig(
    enabled=True,
    model="openai:gpt-4o",
    conversation_persistence=ConversationPersistenceConfig(
        enabled=True,
        db_url="sqlite:///data/conversations.db",
    ),
)

# Create AI agent
agent = AIAgent(config)
```

## Best Practices

### 1. Use Appropriate Database

```python
# Development: SQLite
manager = PersistentConversationManager(
    db_url="sqlite:///data/conversations.db",
)

# Production: PostgreSQL or MySQL
manager = PersistentConversationManager(
    db_url="postgresql://user:pass@localhost/conversations",
)
```

### 2. Regular Cleanup

```python
# Clean up old conversations regularly
@scheduler.scheduled_job('cron', day=1)  # Monthly
def monthly_cleanup():
    # Delete very old conversations
    manager.cleanup_old_conversations(days=90)

    # Export important conversations before deletion
    important_users = get_important_users()
    for user_key in important_users:
        conv = manager.get_conversation_by_user(user_key)
        if conv:
            data = manager.export_conversation(conv.id)
            save_to_archive(user_key, data)
```

### 3. Monitor Statistics

```python
# Periodically check stats
stats = manager.get_stats()

if stats['total_tokens'] > 1000000:
    logger.warning("High token usage: %d", stats['total_tokens'])

if stats['total_conversations'] > 10000:
    logger.info("Consider cleanup: %d conversations", stats['total_conversations'])
```

### 4. Handle Errors Gracefully

```python
try:
    conv = manager.get_or_create(user_key, platform, chat_id)
except Exception as e:
    logger.error("Failed to get/create conversation: %s", e)
    # Fall back to in-memory conversation
    conv = create_temporary_conversation(user_key)
```

### 5. Backup Important Data

```python
import json
from datetime import datetime

def backup_all_conversations():
    """Backup all conversations to JSON files."""
    session = manager.get_session()
    try:
        convs = session.query(ConversationRecord).all()

        backup_dir = f"backups/{datetime.now().strftime('%Y%m%d')}"
        os.makedirs(backup_dir, exist_ok=True)

        for conv in convs:
            data = manager.export_conversation(conv.id)
            filename = f"{backup_dir}/{conv.user_key.replace(':', '_')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

        logger.info("Backed up %d conversations", len(convs))
    finally:
        session.close()
```

### 6. Token Budget Management

```python
async def check_token_budget(user_key: str, budget: int = 100000):
    """Check if user is within token budget."""
    conv = manager.get_conversation_by_user(user_key)

    if conv and conv.total_tokens >= budget:
        logger.warning(
            "User %s exceeded token budget: %d/%d",
            user_key, conv.total_tokens, budget
        )
        return False

    return True
```

## See Also

- [AI Commands](commands.md) - Command system for conversations
- [AI Enhancements](enhancements.md) - Advanced AI features
- [AI Multi-Provider](multi-provider.md) - AI provider configuration
- [Chat Controller Guide](../guides/chat-controller-guide.md) - Unified chat handling
