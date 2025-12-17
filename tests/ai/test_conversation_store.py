"""Tests for persistent conversation storage."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from feishu_webhook_bot.ai.conversation_store import (
    ConversationRecord,
    MessageRecord,
    PersistentConversationManager,
)


@pytest.fixture
def temp_db_dir() -> Path:
    """Create a temporary directory for the database."""
    import shutil

    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    # Cleanup with retry for Windows file locking issues
    try:
        shutil.rmtree(tmpdir)
    except Exception:
        pass  # File may be locked, ignore


@pytest.fixture
def manager(temp_db_dir: Path) -> PersistentConversationManager:
    """Create a manager with an in-memory database."""
    return PersistentConversationManager(
        db_url=f"sqlite:///{temp_db_dir / 'test.db'}",
        echo=False,
    )


class TestConversationStore:
    """Test conversation storage and retrieval."""

    def test_init_creates_tables(self, temp_db_dir: Path) -> None:
        """Test that initialization creates database tables."""
        manager = PersistentConversationManager(db_url=f"sqlite:///{temp_db_dir / 'test.db'}")
        from sqlalchemy import inspect

        inspector = inspect(manager.engine)
        tables = inspector.get_table_names()
        assert "conversations" in tables
        assert "messages" in tables

    def test_get_or_create_new_conversation(self, manager: PersistentConversationManager) -> None:
        """Test creating a new conversation."""
        conv = manager.get_or_create("user123", "feishu", "chat456")

        assert conv.user_key == "user123"
        assert conv.platform == "feishu"
        assert conv.chat_id == "chat456"
        assert conv.message_count == 0
        assert conv.total_tokens == 0
        assert conv.created_at is not None

    def test_get_or_create_existing_conversation(
        self, manager: PersistentConversationManager
    ) -> None:
        """Test retrieving existing conversation."""
        conv1 = manager.get_or_create("user123", "feishu", "chat456")
        conv_id1 = conv1.id

        conv2 = manager.get_or_create("user123", "feishu", "chat456")
        conv_id2 = conv2.id

        assert conv_id1 == conv_id2

    def test_save_message(self, manager: PersistentConversationManager) -> None:
        """Test saving messages."""
        conv = manager.get_or_create("user123", "feishu", "chat456")

        msg = manager.save_message(conv.id, "user", "Hello", tokens=10)

        assert msg.conversation_id == conv.id
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tokens == 10

    def test_save_message_with_metadata(self, manager: PersistentConversationManager) -> None:
        """Test saving message with metadata."""
        conv = manager.get_or_create("user123", "feishu", "chat456")

        metadata = {"tool": "search", "query": "test"}
        msg = manager.save_message(conv.id, "tool", "result", tokens=5, metadata=metadata)

        assert msg.get_metadata() == metadata

    def test_save_message_invalid_conversation(
        self, manager: PersistentConversationManager
    ) -> None:
        """Test saving message to non-existent conversation."""
        with pytest.raises(ValueError):
            manager.save_message(999, "user", "Hello")

    def test_load_history(self, manager: PersistentConversationManager) -> None:
        """Test loading conversation history."""
        conv = manager.get_or_create("user123", "feishu", "chat456")

        manager.save_message(conv.id, "user", "Hello", tokens=10)
        manager.save_message(conv.id, "assistant", "Hi there", tokens=15)

        history = manager.load_history(conv.id)

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there"

    def test_load_history_max_turns(self, manager: PersistentConversationManager) -> None:
        """Test loading history with max_turns limit."""
        conv = manager.get_or_create("user123", "feishu", "chat456")

        # Add 6 messages (3 turns)
        for i in range(6):
            manager.save_message(conv.id, "user" if i % 2 == 0 else "assistant", f"Message {i}")

        history = manager.load_history(conv.id, max_turns=2)

        # Should return at most 4 messages (2 turns * 2)
        assert len(history) == 4

    def test_get_conversation_by_user(self, manager: PersistentConversationManager) -> None:
        """Test retrieving conversation by user key."""
        conv = manager.get_or_create("user123", "feishu", "chat456")

        retrieved = manager.get_conversation_by_user("user123")

        assert retrieved is not None
        assert retrieved.id == conv.id

    def test_get_conversation_by_user_not_found(
        self, manager: PersistentConversationManager
    ) -> None:
        """Test retrieving non-existent conversation."""
        result = manager.get_conversation_by_user("nonexistent")
        assert result is None

    def test_update_conversation_stats(self, manager: PersistentConversationManager) -> None:
        """Test updating conversation statistics."""
        conv = manager.get_or_create("user123", "feishu", "chat456")
        initial_tokens = conv.total_tokens

        manager.update_conversation_stats(conv.id, 100)

        # Retrieve updated conversation
        updated = manager.get_conversation_by_user("user123")
        assert updated.total_tokens == initial_tokens + 100

    def test_update_conversation_stats_invalid(
        self, manager: PersistentConversationManager
    ) -> None:
        """Test updating stats for non-existent conversation."""
        with pytest.raises(ValueError):
            manager.update_conversation_stats(999, 100)

    def test_clear_conversation(self, manager: PersistentConversationManager) -> None:
        """Test clearing conversation history."""
        conv = manager.get_or_create("user123", "feishu", "chat456")

        manager.save_message(conv.id, "user", "Hello")
        manager.save_message(conv.id, "assistant", "Hi")

        manager.clear_conversation(conv.id)

        history = manager.load_history(conv.id)
        assert len(history) == 0

        # Check stats were reset
        updated = manager.get_conversation_by_user("user123")
        assert updated.message_count == 0
        assert updated.total_tokens == 0

    def test_delete_conversation(self, manager: PersistentConversationManager) -> None:
        """Test deleting a conversation."""
        conv = manager.get_or_create("user123", "feishu", "chat456")
        conv_id = conv.id

        manager.save_message(conv.id, "user", "Hello")

        manager.delete_conversation(conv_id)

        result = manager.get_conversation_by_user("user123")
        assert result is None

    def test_cleanup_old_conversations(self, manager: PersistentConversationManager) -> None:
        """Test cleaning up old conversations."""
        # Create a conversation
        conv = manager.get_or_create("user123", "feishu", "chat456")

        # Manually set last_activity to old date
        session = manager.get_session()
        old_date = datetime.now(UTC) - timedelta(days=40)
        session.query(ConversationRecord).filter_by(id=conv.id).update({"last_activity": old_date})
        session.commit()
        session.close()

        # Cleanup conversations older than 30 days
        count = manager.cleanup_old_conversations(days=30)

        assert count == 1
        result = manager.get_conversation_by_user("user123")
        assert result is None

    def test_cleanup_keeps_recent_conversations(
        self, manager: PersistentConversationManager
    ) -> None:
        """Test that cleanup doesn't remove recent conversations."""
        manager.get_or_create("user123", "feishu", "chat456")

        count = manager.cleanup_old_conversations(days=30)

        assert count == 0
        result = manager.get_conversation_by_user("user123")
        assert result is not None

    def test_export_conversation(self, manager: PersistentConversationManager) -> None:
        """Test exporting conversation."""
        conv = manager.get_or_create("user123", "feishu", "chat456")
        manager.set_active_persona_id("user123", "developer", platform="feishu")
        manager.save_message(conv.id, "user", "Hello", tokens=10)
        manager.save_message(conv.id, "assistant", "Hi", tokens=15)

        data = manager.export_conversation(conv.id)

        assert data["conversation"]["user_key"] == "user123"
        assert data["conversation"]["active_persona_id"] == "developer"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "Hello"

    def test_import_conversation(self, manager: PersistentConversationManager) -> None:
        """Test importing conversation."""
        export_data = {
            "conversation": {
                "user_key": "user456",
                "platform": "qq",
                "chat_id": "chat789",
                "summary": None,
                "active_persona_id": "developer",
                "total_tokens": 100,
                "message_count": 2,
                "created_at": datetime.now(UTC).isoformat(),
                "last_activity": datetime.now(UTC).isoformat(),
            },
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "tokens": 10,
                    "metadata": None,
                },
                {
                    "role": "assistant",
                    "content": "Hi",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "tokens": 15,
                    "metadata": None,
                },
            ],
        }

        imported_conv = manager.import_conversation(export_data)

        assert imported_conv.user_key == "user456"
        assert imported_conv.platform == "qq"
        assert imported_conv.active_persona_id == "developer"

        history = manager.load_history(imported_conv.id)
        assert len(history) == 2

    def test_set_and_get_active_persona_id(self, manager: PersistentConversationManager) -> None:
        user_key = "feishu:group:user123"
        manager.get_or_create(user_key, "feishu", "chat456")

        assert manager.get_active_persona_id(user_key) is None

        manager.set_active_persona_id(user_key, "developer", platform="feishu", chat_id="chat456")
        assert manager.get_active_persona_id(user_key) == "developer"

        conv = manager.get_conversation_by_user(user_key)
        assert conv is not None
        assert conv.active_persona_id == "developer"

    def test_import_duplicate_conversation(self, manager: PersistentConversationManager) -> None:
        """Test that importing duplicate conversation returns existing."""
        conv1 = manager.get_or_create("user789", "feishu", "chat000")

        export_data = {
            "conversation": {
                "user_key": "user789",
                "platform": "feishu",
                "chat_id": "chat000",
                "summary": None,
                "total_tokens": 0,
                "message_count": 0,
                "created_at": datetime.now(UTC).isoformat(),
                "last_activity": datetime.now(UTC).isoformat(),
            },
            "messages": [],
        }

        imported_conv = manager.import_conversation(export_data)

        assert imported_conv.id == conv1.id

    def test_get_stats(self, manager: PersistentConversationManager) -> None:
        """Test getting conversation statistics."""
        conv1 = manager.get_or_create("user1", "feishu", "chat1")
        manager.save_message(conv1.id, "user", "Hello", tokens=10)
        manager.save_message(conv1.id, "assistant", "Hi", tokens=15)

        conv2 = manager.get_or_create("user2", "qq", "chat2")
        manager.save_message(conv2.id, "user", "Hey", tokens=5)

        stats = manager.get_stats()

        assert stats["total_conversations"] == 2
        assert stats["total_messages"] == 3
        assert stats["total_tokens"] == 30
        assert stats["average_tokens_per_conversation"] == 15.0

    def test_conversation_record_to_dict(self) -> None:
        """Test converting conversation record to dict."""
        conv = ConversationRecord(
            user_key="test_user",
            platform="feishu",
            chat_id="test_chat",
            total_tokens=100,
            message_count=5,
        )

        data = conv.to_dict()

        assert data["user_key"] == "test_user"
        assert data["platform"] == "feishu"
        assert data["total_tokens"] == 100

    def test_message_record_to_dict(self) -> None:
        """Test converting message record to dict."""
        msg = MessageRecord(
            conversation_id=1,
            role="user",
            content="Test message",
            tokens=10,
        )

        data = msg.to_dict()

        assert data["role"] == "user"
        assert data["content"] == "Test message"
        assert data["tokens"] == 10

    def test_message_record_metadata(self) -> None:
        """Test message metadata handling."""
        metadata = {"tool": "search", "query": "test"}
        msg = MessageRecord(
            conversation_id=1,
            role="tool",
            content="result",
            metadata_json=json.dumps(metadata),
        )

        parsed = msg.get_metadata()
        assert parsed == metadata

    def test_message_record_invalid_metadata(self) -> None:
        """Test handling of invalid JSON metadata."""
        msg = MessageRecord(
            conversation_id=1,
            role="user",
            content="test",
            metadata_json="invalid json",
        )

        parsed = msg.get_metadata()
        assert parsed == {}


class TestConversationStoreThreadSafety:
    """Test thread safety of conversation store."""

    def test_concurrent_operations(self, manager: PersistentConversationManager) -> None:
        """Test that concurrent operations don't cause issues."""
        import threading

        results = []

        def create_and_save(user_id: str) -> None:
            try:
                conv = manager.get_or_create(user_id, "feishu", "chat123")
                for i in range(5):
                    manager.save_message(conv.id, "user", f"Message {i}")
                results.append(True)
            except Exception as e:
                results.append(False)
                print(f"Error: {e}")

        threads = [threading.Thread(target=create_and_save, args=(f"user{i}",)) for i in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert all(results)
        stats = manager.get_stats()
        assert stats["total_conversations"] == 5
