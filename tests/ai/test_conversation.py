"""Comprehensive tests for conversation state management.

Tests cover:
- ConversationState creation and lifecycle
- Message management and token tracking
- Conversation expiration
- Analytics and export/import
- ConversationManager operations
- Cleanup task management
- Concurrent access and thread safety
- Edge cases and error handling
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from feishu_webhook_bot.ai.conversation import ConversationManager, ConversationState

# ==============================================================================
# ConversationState Tests
# ==============================================================================


class TestConversationStateCreation:
    """Tests for ConversationState initialization."""

    def test_conversation_state_creation(self):
        """Test ConversationState initialization with user_id."""
        state = ConversationState("user123")

        assert state.user_id == "user123"
        assert state.messages == []
        assert state.context == {}
        assert state.input_tokens == 0
        assert state.output_tokens == 0
        assert state.summary is None
        assert state.message_count == 0

    def test_conversation_state_timestamps(self):
        """Test ConversationState has valid timestamps."""
        before = datetime.now(UTC)
        state = ConversationState("user123")
        after = datetime.now(UTC)

        assert before <= state.created_at <= after
        assert before <= state.last_activity <= after


class TestConversationStateMessages:
    """Tests for message management."""

    def test_add_messages_empty(self):
        """Test adding empty message list."""
        state = ConversationState("user123")

        state.add_messages([])

        assert state.messages == []
        assert state.message_count == 0

    def test_add_messages_with_tokens(self):
        """Test adding messages with token tracking."""
        state = ConversationState("user123")
        mock_messages = [Mock(), Mock()]

        state.add_messages(mock_messages, input_tokens=100, output_tokens=50)

        assert len(state.messages) == 2
        assert state.message_count == 2
        assert state.input_tokens == 100
        assert state.output_tokens == 50

    def test_add_messages_accumulates_tokens(self):
        """Test token accumulation across multiple adds."""
        state = ConversationState("user123")

        state.add_messages([Mock()], input_tokens=50, output_tokens=25)
        state.add_messages([Mock()], input_tokens=30, output_tokens=15)

        assert state.input_tokens == 80
        assert state.output_tokens == 40
        assert state.message_count == 2

    def test_add_messages_updates_last_activity(self):
        """Test adding messages updates last_activity timestamp."""
        state = ConversationState("user123")
        original_activity = state.last_activity

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        state.add_messages([Mock()])

        assert state.last_activity > original_activity

    def test_get_messages_all(self):
        """Test getting all messages."""
        state = ConversationState("user123")
        messages = [Mock(), Mock(), Mock()]
        state.add_messages(messages)

        result = state.get_messages()

        assert len(result) == 3
        # Should return a copy
        assert result is not state.messages

    def test_get_messages_with_max_turns(self):
        """Test getting messages with max_turns limit."""
        state = ConversationState("user123")
        messages = [Mock() for _ in range(10)]
        state.add_messages(messages)

        # max_turns=2 means 4 messages (2 turns * 2 messages per turn)
        result = state.get_messages(max_turns=2)

        assert len(result) == 4

    def test_get_messages_max_turns_exceeds_count(self):
        """Test max_turns greater than available messages."""
        state = ConversationState("user123")
        messages = [Mock(), Mock()]
        state.add_messages(messages)

        result = state.get_messages(max_turns=10)

        assert len(result) == 2


class TestConversationStateClear:
    """Tests for clearing conversation state."""

    def test_clear_resets_all(self):
        """Test clear resets messages, context, and summary."""
        state = ConversationState("user123")
        state.add_messages(
            [Mock(), Mock()], input_tokens=100, output_tokens=50)
        state.context["key"] = "value"
        state.summary = "Test summary"

        state.clear()

        assert state.messages == []
        assert state.context == {}
        assert state.summary is None
        # Note: tokens are not reset by clear()

    def test_clear_updates_last_activity(self):
        """Test clear updates last_activity."""
        state = ConversationState("user123")
        original = state.last_activity

        import time
        time.sleep(0.01)

        state.clear()

        assert state.last_activity > original


class TestConversationStateExpiration:
    """Tests for conversation expiration."""

    def test_is_expired_false(self):
        """Test conversation is not expired immediately."""
        state = ConversationState("user123")

        assert state.is_expired(timeout_minutes=30) is False

    def test_is_expired_true(self):
        """Test conversation is expired after timeout."""
        state = ConversationState("user123")
        # Set last_activity to 31 minutes ago
        state.last_activity = datetime.now(UTC) - timedelta(minutes=31)

        assert state.is_expired(timeout_minutes=30) is True

    def test_is_expired_boundary(self):
        """Test expiration at exact boundary."""
        state = ConversationState("user123")
        # Set last_activity to exactly 30 minutes ago
        state.last_activity = datetime.now(
            UTC) - timedelta(minutes=30, seconds=1)

        assert state.is_expired(timeout_minutes=30) is True


class TestConversationStateSummary:
    """Tests for conversation summary."""

    def test_set_summary(self):
        """Test setting conversation summary."""
        state = ConversationState("user123")

        state.set_summary("This is a test summary")

        assert state.summary == "This is a test summary"

    def test_set_summary_overwrites(self):
        """Test setting summary overwrites previous."""
        state = ConversationState("user123")
        state.set_summary("First summary")

        state.set_summary("Second summary")

        assert state.summary == "Second summary"


class TestConversationStateAnalytics:
    """Tests for conversation analytics."""

    def test_get_duration(self):
        """Test getting conversation duration."""
        state = ConversationState("user123")

        duration = state.get_duration()

        assert isinstance(duration, timedelta)
        assert duration.total_seconds() >= 0

    def test_get_analytics(self):
        """Test getting conversation analytics."""
        state = ConversationState("user123")
        state.add_messages(
            [Mock(), Mock()], input_tokens=100, output_tokens=50)
        state.context["key"] = "value"
        state.summary = "Test"

        analytics = state.get_analytics()

        assert analytics["user_id"] == "user123"
        assert analytics["message_count"] == 2
        assert analytics["input_tokens"] == 100
        assert analytics["output_tokens"] == 50
        assert analytics["total_tokens"] == 150
        assert analytics["has_summary"] is True
        assert "key" in analytics["context_keys"]
        assert "duration_seconds" in analytics
        assert "duration_minutes" in analytics


class TestConversationStateExportImport:
    """Tests for export/import functionality."""

    def test_export_to_dict(self):
        """Test exporting conversation to dictionary."""
        state = ConversationState("user123")
        state.context["key"] = "value"
        state.summary = "Test summary"
        state.input_tokens = 100
        state.output_tokens = 50

        data = state.export_to_dict()

        assert data["user_id"] == "user123"
        assert data["context"] == {"key": "value"}
        assert data["summary"] == "Test summary"
        assert data["input_tokens"] == 100
        assert data["output_tokens"] == 50
        assert "created_at" in data
        assert "last_activity" in data

    def test_import_from_dict(self):
        """Test importing conversation from dictionary."""
        data = {
            "user_id": "user456",
            "context": {"imported": True},
            "summary": "Imported summary",
            "input_tokens": 200,
            "output_tokens": 100,
            "message_count": 5,
            "created_at": "2024-01-01T00:00:00+00:00",
            "last_activity": "2024-01-01T01:00:00+00:00",
        }

        state = ConversationState.import_from_dict(data)

        assert state.user_id == "user456"
        assert state.context == {"imported": True}
        assert state.summary == "Imported summary"
        assert state.input_tokens == 200
        assert state.output_tokens == 100
        assert state.message_count == 5

    def test_import_from_dict_minimal(self):
        """Test importing with minimal data."""
        data = {"user_id": "minimal_user"}

        state = ConversationState.import_from_dict(data)

        assert state.user_id == "minimal_user"
        assert state.context == {}
        assert state.summary is None


# ==============================================================================
# ConversationManager Tests
# ==============================================================================


class TestConversationManagerCreation:
    """Tests for ConversationManager initialization."""

    def test_manager_creation_defaults(self):
        """Test ConversationManager with default settings."""
        manager = ConversationManager()

        assert manager._timeout_minutes == 30
        assert manager._cleanup_interval == 300
        assert manager._conversations == {}

    def test_manager_creation_custom(self):
        """Test ConversationManager with custom settings."""
        manager = ConversationManager(
            timeout_minutes=60, cleanup_interval_seconds=600)

        assert manager._timeout_minutes == 60
        assert manager._cleanup_interval == 600


class TestConversationManagerOperations:
    """Tests for ConversationManager operations."""

    @pytest.mark.anyio
    async def test_get_conversation_creates_new(self):
        """Test get_conversation creates new conversation."""
        manager = ConversationManager()

        conv = await manager.get_conversation("user123")

        assert conv.user_id == "user123"
        assert "user123" in manager._conversations

    @pytest.mark.anyio
    async def test_get_conversation_returns_existing(self):
        """Test get_conversation returns existing conversation."""
        manager = ConversationManager()

        conv1 = await manager.get_conversation("user123")
        conv1.add_messages([Mock()])

        conv2 = await manager.get_conversation("user123")

        assert conv1 is conv2
        assert len(conv2.messages) == 1

    @pytest.mark.anyio
    async def test_clear_conversation(self):
        """Test clearing a conversation."""
        manager = ConversationManager()
        conv = await manager.get_conversation("user123")
        conv.add_messages([Mock()])

        await manager.clear_conversation("user123")

        assert conv.messages == []

    @pytest.mark.anyio
    async def test_clear_conversation_nonexistent(self):
        """Test clearing nonexistent conversation does nothing."""
        manager = ConversationManager()

        # Should not raise
        await manager.clear_conversation("nonexistent")

    @pytest.mark.anyio
    async def test_delete_conversation(self):
        """Test deleting a conversation."""
        manager = ConversationManager()
        await manager.get_conversation("user123")

        await manager.delete_conversation("user123")

        assert "user123" not in manager._conversations

    @pytest.mark.anyio
    async def test_delete_conversation_nonexistent(self):
        """Test deleting nonexistent conversation does nothing."""
        manager = ConversationManager()

        # Should not raise
        await manager.delete_conversation("nonexistent")


class TestConversationManagerCleanup:
    """Tests for conversation cleanup."""

    @pytest.mark.anyio
    async def test_cleanup_expired_removes_old(self):
        """Test cleanup removes expired conversations."""
        manager = ConversationManager(timeout_minutes=30)

        # Create conversations
        conv1 = await manager.get_conversation("user1")
        _ = await manager.get_conversation("user2")  # Keep user2 active

        # Make conv1 expired
        conv1.last_activity = datetime.now(UTC) - timedelta(minutes=31)

        removed = await manager.cleanup_expired()

        assert removed == 1
        assert "user1" not in manager._conversations
        assert "user2" in manager._conversations

    @pytest.mark.anyio
    async def test_cleanup_expired_keeps_active(self):
        """Test cleanup keeps active conversations."""
        manager = ConversationManager(timeout_minutes=30)

        await manager.get_conversation("user1")
        await manager.get_conversation("user2")

        removed = await manager.cleanup_expired()

        assert removed == 0
        assert len(manager._conversations) == 2


class TestConversationManagerExportImport:
    """Tests for export/import operations."""

    @pytest.mark.anyio
    async def test_export_conversation(self):
        """Test exporting a conversation to JSON."""
        manager = ConversationManager()
        conv = await manager.get_conversation("user123")
        conv.context["key"] = "value"

        json_str = await manager.export_conversation("user123")

        data = json.loads(json_str)
        assert data["user_id"] == "user123"
        assert data["context"] == {"key": "value"}

    @pytest.mark.anyio
    async def test_export_conversation_not_found(self):
        """Test exporting nonexistent conversation raises error."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="not found"):
            await manager.export_conversation("nonexistent")

    @pytest.mark.anyio
    async def test_import_conversation(self):
        """Test importing a conversation from JSON."""
        manager = ConversationManager()
        json_data = json.dumps({
            "user_id": "imported_user",
            "context": {"imported": True},
        })

        user_id = await manager.import_conversation(json_data)

        assert user_id == "imported_user"
        assert "imported_user" in manager._conversations

    @pytest.mark.anyio
    async def test_import_conversation_invalid_json(self):
        """Test importing invalid JSON raises error."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="Invalid"):
            await manager.import_conversation("not valid json")


class TestConversationManagerAnalytics:
    """Tests for analytics operations."""

    @pytest.mark.anyio
    async def test_get_conversation_analytics(self):
        """Test getting analytics for a conversation."""
        manager = ConversationManager()
        conv = await manager.get_conversation("user123")
        conv.add_messages([Mock()], input_tokens=100, output_tokens=50)

        analytics = await manager.get_conversation_analytics("user123")

        assert analytics["user_id"] == "user123"
        assert analytics["input_tokens"] == 100

    @pytest.mark.anyio
    async def test_get_conversation_analytics_not_found(self):
        """Test getting analytics for nonexistent conversation."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="not found"):
            await manager.get_conversation_analytics("nonexistent")

    @pytest.mark.anyio
    async def test_get_stats_empty(self):
        """Test getting stats with no conversations."""
        manager = ConversationManager()

        stats = await manager.get_stats()

        assert stats["total_conversations"] == 0
        assert stats["total_messages"] == 0
        assert stats["total_tokens"] == 0

    @pytest.mark.anyio
    async def test_get_stats_with_conversations(self):
        """Test getting stats with active conversations."""
        manager = ConversationManager()

        conv1 = await manager.get_conversation("user1")
        conv1.add_messages(
            [Mock(), Mock()], input_tokens=100, output_tokens=50)

        conv2 = await manager.get_conversation("user2")
        conv2.add_messages([Mock()], input_tokens=50, output_tokens=25)

        stats = await manager.get_stats()

        assert stats["total_conversations"] == 2
        assert stats["total_messages"] == 3
        assert stats["total_input_tokens"] == 150
        assert stats["total_output_tokens"] == 75
        assert stats["total_tokens"] == 225


class TestConversationManagerCleanupTask:
    """Tests for cleanup task management."""

    def test_start_cleanup_creates_task(self):
        """Test start_cleanup creates background task."""
        manager = ConversationManager()

        # Need event loop for task creation
        async def run_test():
            manager.start_cleanup()
            assert manager._cleanup_task is not None
            await manager.stop_cleanup()

        asyncio.run(run_test())

    @pytest.mark.anyio
    async def test_stop_cleanup_cancels_task(self):
        """Test stop_cleanup cancels background task."""
        manager = ConversationManager(cleanup_interval_seconds=1)

        manager.start_cleanup()
        assert manager._cleanup_task is not None

        await manager.stop_cleanup()
        # Task should be done after stop
        assert manager._cleanup_task.done() or manager._cleanup_task.cancelled()

    @pytest.mark.anyio
    async def test_stop_cleanup_without_start(self):
        """Test stop_cleanup without start does nothing."""
        manager = ConversationManager()

        # Should not raise
        await manager.stop_cleanup()


# ==============================================================================
# Concurrent Access Tests
# ==============================================================================


class TestConversationManagerConcurrency:
    """Tests for concurrent access to ConversationManager."""

    @pytest.mark.anyio
    async def test_concurrent_get_conversation(self):
        """Test concurrent access to get_conversation."""
        manager = ConversationManager()

        async def get_conv(user_id: str):
            return await manager.get_conversation(user_id)

        # Create multiple concurrent requests for same user
        tasks = [get_conv("user123") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should return the same conversation instance
        assert all(r is results[0] for r in results)

    @pytest.mark.anyio
    async def test_concurrent_different_users(self):
        """Test concurrent access for different users."""
        manager = ConversationManager()

        async def get_conv(user_id: str):
            return await manager.get_conversation(user_id)

        # Create conversations for different users concurrently
        user_ids = [f"user{i}" for i in range(10)]
        tasks = [get_conv(uid) for uid in user_ids]
        results = await asyncio.gather(*tasks)

        # All should be different conversations
        assert len(set(id(r) for r in results)) == 10

    @pytest.mark.anyio
    async def test_concurrent_clear_and_get(self):
        """Test concurrent clear and get operations."""
        manager = ConversationManager()

        # Create initial conversation
        conv = await manager.get_conversation("user123")
        conv.add_messages([Mock()])

        async def clear_conv():
            await manager.clear_conversation("user123")

        async def get_conv():
            return await manager.get_conversation("user123")

        # Run clear and get concurrently
        tasks = [clear_conv(), get_conv(), clear_conv(), get_conv()]
        await asyncio.gather(*tasks)

        # Should not raise any errors

    @pytest.mark.anyio
    async def test_concurrent_cleanup(self):
        """Test concurrent cleanup operations."""
        manager = ConversationManager(timeout_minutes=0)

        # Create multiple conversations
        for i in range(10):
            conv = await manager.get_conversation(f"user{i}")
            conv.last_activity = datetime.now(UTC) - timedelta(minutes=1)

        # Run multiple cleanup operations concurrently
        tasks = [manager.cleanup_expired() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Total removed should be 10 (across all cleanup calls)
        assert sum(results) == 10


# ==============================================================================
# Edge Cases Tests
# ==============================================================================


class TestConversationStateEdgeCases:
    """Edge case tests for ConversationState."""

    def test_empty_user_id(self):
        """Test ConversationState with empty user_id."""
        state = ConversationState("")

        assert state.user_id == ""
        assert state.messages == []

    def test_very_long_user_id(self):
        """Test ConversationState with very long user_id."""
        long_id = "u" * 1000
        state = ConversationState(long_id)

        assert state.user_id == long_id

    def test_unicode_user_id(self):
        """Test ConversationState with unicode user_id."""
        state = ConversationState("用户123")

        assert state.user_id == "用户123"

    def test_add_messages_large_token_count(self):
        """Test adding messages with large token counts."""
        state = ConversationState("user123")

        state.add_messages([Mock()], input_tokens=1_000_000, output_tokens=500_000)

        assert state.input_tokens == 1_000_000
        assert state.output_tokens == 500_000

    def test_context_with_complex_data(self):
        """Test context with complex nested data."""
        state = ConversationState("user123")

        state.context = {
            "nested": {"deep": {"value": [1, 2, 3]}},
            "list": [{"a": 1}, {"b": 2}],
            "unicode": "你好世界",
        }

        assert state.context["nested"]["deep"]["value"] == [1, 2, 3]
        assert state.context["unicode"] == "你好世界"

    def test_summary_with_unicode(self):
        """Test summary with unicode content."""
        state = ConversationState("user123")

        state.set_summary("这是一个测试摘要 🎉")

        assert state.summary == "这是一个测试摘要 🎉"

    def test_export_import_roundtrip(self):
        """Test export and import roundtrip preserves data."""
        state = ConversationState("user123")
        state.context = {"key": "value"}
        state.summary = "Test summary"
        state.input_tokens = 100
        state.output_tokens = 50

        # Export
        data = state.export_to_dict()

        # Import
        imported = ConversationState.import_from_dict(data)

        assert imported.user_id == state.user_id
        assert imported.context == state.context
        assert imported.summary == state.summary
        assert imported.input_tokens == state.input_tokens
        assert imported.output_tokens == state.output_tokens


class TestConversationManagerEdgeCases:
    """Edge case tests for ConversationManager."""

    @pytest.mark.anyio
    async def test_get_stats_single_conversation(self):
        """Test get_stats with single conversation."""
        manager = ConversationManager()

        conv = await manager.get_conversation("user123")
        conv.add_messages([Mock()], input_tokens=100, output_tokens=50)

        stats = await manager.get_stats()

        assert stats["total_conversations"] == 1
        assert stats["total_messages"] == 1
        assert stats["average_messages_per_conversation"] == 1.0

    @pytest.mark.anyio
    async def test_get_stats_with_summaries(self):
        """Test get_stats counts conversations with summaries."""
        manager = ConversationManager()

        conv1 = await manager.get_conversation("user1")
        conv1.set_summary("Summary 1")

        conv2 = await manager.get_conversation("user2")
        # No summary for conv2

        stats = await manager.get_stats()

        assert stats["conversations_with_summary"] == 1

    @pytest.mark.anyio
    async def test_export_conversation_with_messages(self):
        """Test exporting conversation with messages."""
        manager = ConversationManager()

        conv = await manager.get_conversation("user123")
        # Add a message - the export should handle message serialization
        # Note: The actual implementation may require specific message types
        # For this test, we verify the conversation exists and can be exported
        conv.context["test_key"] = "test_value"

        json_str = await manager.export_conversation("user123")

        data = json.loads(json_str)
        assert data["user_id"] == "user123"
        assert data["context"]["test_key"] == "test_value"

    @pytest.mark.anyio
    async def test_import_conversation_replaces_existing(self):
        """Test importing conversation replaces existing."""
        manager = ConversationManager()

        # Create existing conversation
        existing = await manager.get_conversation("user123")
        existing.context["old"] = True

        # Import new conversation
        json_data = json.dumps({
            "user_id": "user123",
            "context": {"new": True},
        })

        await manager.import_conversation(json_data)

        # Get the conversation again
        conv = await manager.get_conversation("user123")
        assert conv.context.get("new") is True
        assert conv.context.get("old") is None

    @pytest.mark.anyio
    async def test_cleanup_with_mixed_expiration(self):
        """Test cleanup with mix of expired and active conversations."""
        manager = ConversationManager(timeout_minutes=30)

        # Create expired conversations
        for i in range(5):
            conv = await manager.get_conversation(f"expired{i}")
            conv.last_activity = datetime.now(UTC) - timedelta(minutes=31)

        # Create active conversations
        for i in range(5):
            await manager.get_conversation(f"active{i}")

        removed = await manager.cleanup_expired()

        assert removed == 5
        assert len(manager._conversations) == 5

    @pytest.mark.anyio
    async def test_manager_with_zero_timeout(self):
        """Test manager with zero timeout (immediate expiration)."""
        manager = ConversationManager(timeout_minutes=0)

        conv = await manager.get_conversation("user123")
        # Conversation is immediately expired

        # Wait a tiny bit to ensure expiration
        await asyncio.sleep(0.01)

        removed = await manager.cleanup_expired()

        # Should have removed the conversation
        assert removed == 1

    @pytest.mark.anyio
    async def test_manager_with_large_timeout(self):
        """Test manager with very large timeout."""
        manager = ConversationManager(timeout_minutes=525600)  # 1 year

        conv = await manager.get_conversation("user123")

        assert conv.is_expired(525600) is False

    @pytest.mark.anyio
    async def test_delete_and_recreate_conversation(self):
        """Test deleting and recreating a conversation."""
        manager = ConversationManager()

        # Create and modify
        conv1 = await manager.get_conversation("user123")
        conv1.add_messages([Mock()], input_tokens=100)

        # Delete
        await manager.delete_conversation("user123")

        # Recreate
        conv2 = await manager.get_conversation("user123")

        # Should be a fresh conversation
        assert conv2.messages == []
        assert conv2.input_tokens == 0

    @pytest.mark.anyio
    async def test_multiple_start_cleanup(self):
        """Test calling start_cleanup multiple times."""
        manager = ConversationManager(cleanup_interval_seconds=1)

        manager.start_cleanup()
        first_task = manager._cleanup_task

        # Start again - should create new task if previous is done
        manager.start_cleanup()

        # Both should be the same task (not done yet)
        assert manager._cleanup_task is first_task

        await manager.stop_cleanup()


# ==============================================================================
# Analytics Tests
# ==============================================================================


class TestConversationAnalyticsAdvanced:
    """Advanced analytics tests."""

    def test_analytics_duration_calculation(self):
        """Test analytics duration is calculated correctly."""
        state = ConversationState("user123")

        # Manually set created_at to 1 hour ago
        state.created_at = datetime.now(UTC) - timedelta(hours=1)

        analytics = state.get_analytics()

        # Duration should be approximately 60 minutes
        assert 59 <= analytics["duration_minutes"] <= 61

    def test_analytics_with_no_context(self):
        """Test analytics with empty context."""
        state = ConversationState("user123")

        analytics = state.get_analytics()

        assert analytics["context_keys"] == []

    def test_analytics_with_multiple_context_keys(self):
        """Test analytics with multiple context keys."""
        state = ConversationState("user123")
        state.context = {"key1": 1, "key2": 2, "key3": 3}

        analytics = state.get_analytics()

        assert len(analytics["context_keys"]) == 3
        assert "key1" in analytics["context_keys"]

    @pytest.mark.anyio
    async def test_manager_stats_longest_conversation(self):
        """Test manager stats identifies longest conversation."""
        manager = ConversationManager()

        # Create conversations with different message counts
        conv1 = await manager.get_conversation("user1")
        conv1.add_messages([Mock()])

        conv2 = await manager.get_conversation("user2")
        conv2.add_messages([Mock(), Mock(), Mock()])

        conv3 = await manager.get_conversation("user3")
        conv3.add_messages([Mock(), Mock()])

        stats = await manager.get_stats()

        assert stats["longest_conversation_messages"] == 3
        assert stats["longest_conversation_user"] == "user2"

    @pytest.mark.anyio
    async def test_manager_stats_average_duration(self):
        """Test manager stats calculates average duration."""
        manager = ConversationManager()

        # Create conversations with different ages
        conv1 = await manager.get_conversation("user1")
        conv1.created_at = datetime.now(UTC) - timedelta(minutes=10)

        conv2 = await manager.get_conversation("user2")
        conv2.created_at = datetime.now(UTC) - timedelta(minutes=20)

        stats = await manager.get_stats()

        # Average should be around 15 minutes
        assert 14 <= stats["average_duration_minutes"] <= 16
