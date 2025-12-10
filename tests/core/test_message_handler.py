"""Tests for core.message_handler module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from feishu_webhook_bot.core.message_handler import (
    IncomingMessage,
    MessageHandler,
    MessageParser,
    get_chat_key,
    get_user_key,
)
from feishu_webhook_bot.core.provider import SendResult


class TestIncomingMessage:
    """Tests for IncomingMessage dataclass."""

    def test_create_basic_message(self) -> None:
        """Test creating a basic incoming message."""
        msg = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="group",
            chat_id="chat_456",
            sender_id="user_789",
            sender_name="Alice",
            content="Hello, world!",
        )

        assert msg.id == "msg_123"
        assert msg.platform == "feishu"
        assert msg.chat_type == "group"
        assert msg.chat_id == "chat_456"
        assert msg.sender_id == "user_789"
        assert msg.sender_name == "Alice"
        assert msg.content == "Hello, world!"
        assert msg.mentions == []
        assert msg.is_at_bot is False
        assert msg.reply_to is None
        assert msg.thread_id is None
        assert msg.raw_content is None
        assert msg.metadata == {}

    def test_create_message_with_all_fields(self) -> None:
        """Test creating a message with all optional fields."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        msg = IncomingMessage(
            id="msg_123",
            platform="qq",
            chat_type="private",
            chat_id="",
            sender_id="123456789",
            sender_name="Bob",
            content="@bot help",
            mentions=["bot_id", "other_user"],
            is_at_bot=True,
            reply_to="msg_100",
            thread_id="thread_001",
            timestamp=timestamp,
            raw_content={"text": "@bot help"},
            metadata={"extra": "data"},
        )

        assert msg.mentions == ["bot_id", "other_user"]
        assert msg.is_at_bot is True
        assert msg.reply_to == "msg_100"
        assert msg.thread_id == "thread_001"
        assert msg.timestamp == timestamp
        assert msg.raw_content == {"text": "@bot help"}
        assert msg.metadata == {"extra": "data"}

    def test_to_dict(self) -> None:
        """Test converting message to dictionary."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        msg = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="group",
            chat_id="chat_456",
            sender_id="user_789",
            sender_name="Alice",
            content="Hello",
            mentions=["user_1"],
            is_at_bot=True,
            reply_to="msg_100",
            thread_id="thread_001",
            timestamp=timestamp,
            raw_content={"text": "Hello"},
            metadata={"key": "value"},
        )

        data = msg.to_dict()

        assert data["id"] == "msg_123"
        assert data["platform"] == "feishu"
        assert data["chat_type"] == "group"
        assert data["chat_id"] == "chat_456"
        assert data["sender_id"] == "user_789"
        assert data["sender_name"] == "Alice"
        assert data["content"] == "Hello"
        assert data["mentions"] == ["user_1"]
        assert data["is_at_bot"] is True
        assert data["reply_to"] == "msg_100"
        assert data["thread_id"] == "thread_001"
        assert data["timestamp"] == "2024-01-15T10:30:00"
        assert data["raw_content"] == {"text": "Hello"}
        assert data["metadata"] == {"key": "value"}

    def test_from_dict(self) -> None:
        """Test creating message from dictionary."""
        data = {
            "id": "msg_123",
            "platform": "feishu",
            "chat_type": "group",
            "chat_id": "chat_456",
            "sender_id": "user_789",
            "sender_name": "Alice",
            "content": "Hello",
            "mentions": ["user_1"],
            "is_at_bot": True,
            "reply_to": "msg_100",
            "thread_id": "thread_001",
            "timestamp": "2024-01-15T10:30:00",
            "raw_content": {"text": "Hello"},
            "metadata": {"key": "value"},
        }

        msg = IncomingMessage.from_dict(data)

        assert msg.id == "msg_123"
        assert msg.platform == "feishu"
        assert msg.chat_type == "group"
        assert msg.chat_id == "chat_456"
        assert msg.sender_id == "user_789"
        assert msg.sender_name == "Alice"
        assert msg.content == "Hello"
        assert msg.mentions == ["user_1"]
        assert msg.is_at_bot is True
        assert msg.reply_to == "msg_100"
        assert msg.thread_id == "thread_001"
        assert msg.timestamp == datetime(2024, 1, 15, 10, 30, 0)
        assert msg.raw_content == {"text": "Hello"}
        assert msg.metadata == {"key": "value"}

    def test_from_dict_minimal(self) -> None:
        """Test creating message from minimal dictionary."""
        data = {
            "id": "msg_123",
            "platform": "qq",
            "chat_type": "private",
            "chat_id": "",
            "sender_id": "123456",
            "sender_name": "User",
            "content": "Hi",
        }

        msg = IncomingMessage.from_dict(data)

        assert msg.id == "msg_123"
        assert msg.mentions == []
        assert msg.is_at_bot is False
        assert msg.reply_to is None
        assert msg.thread_id is None
        assert msg.metadata == {}

    def test_from_dict_with_none_timestamp(self) -> None:
        """Test creating message with None timestamp."""
        data = {
            "id": "msg_123",
            "platform": "feishu",
            "chat_type": "group",
            "chat_id": "chat_456",
            "sender_id": "user_789",
            "sender_name": "Alice",
            "content": "Hello",
            "timestamp": None,
        }

        msg = IncomingMessage.from_dict(data)

        assert msg.timestamp is not None
        assert isinstance(msg.timestamp, datetime)

    def test_repr(self) -> None:
        """Test string representation."""
        msg = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="group",
            chat_id="chat_456",
            sender_id="user_789",
            sender_name="Alice",
            content="Hello",
        )

        repr_str = repr(msg)

        assert "msg_123" in repr_str
        assert "feishu" in repr_str
        assert "Alice" in repr_str
        assert "user_789" in repr_str

    def test_roundtrip_serialization(self) -> None:
        """Test that to_dict and from_dict are inverse operations."""
        original = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="group",
            chat_id="chat_456",
            sender_id="user_789",
            sender_name="Alice",
            content="Hello",
            mentions=["user_1"],
            is_at_bot=True,
            reply_to="msg_100",
            thread_id="thread_001",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            raw_content={"text": "Hello"},
            metadata={"key": "value"},
        )

        data = original.to_dict()
        restored = IncomingMessage.from_dict(data)

        assert restored.id == original.id
        assert restored.platform == original.platform
        assert restored.chat_type == original.chat_type
        assert restored.chat_id == original.chat_id
        assert restored.sender_id == original.sender_id
        assert restored.sender_name == original.sender_name
        assert restored.content == original.content
        assert restored.mentions == original.mentions
        assert restored.is_at_bot == original.is_at_bot
        assert restored.reply_to == original.reply_to
        assert restored.thread_id == original.thread_id
        assert restored.timestamp == original.timestamp
        assert restored.raw_content == original.raw_content
        assert restored.metadata == original.metadata


class TestMessageHandlerProtocol:
    """Tests for MessageHandler protocol."""

    def test_protocol_check(self) -> None:
        """Test that classes implementing the protocol are recognized."""

        class MyHandler:
            async def handle_message(self, message: IncomingMessage) -> str | None:
                return "response"

            async def send_reply(
                self,
                message: IncomingMessage,
                reply: str,
                reply_in_thread: bool = True,
            ) -> SendResult:
                return SendResult.ok("reply_id")

        handler = MyHandler()
        assert isinstance(handler, MessageHandler)

    def test_incomplete_implementation_not_recognized(self) -> None:
        """Test that incomplete implementations are not recognized."""

        class IncompleteHandler:
            async def handle_message(self, message: IncomingMessage) -> str | None:
                return None

        handler = IncompleteHandler()
        assert not isinstance(handler, MessageHandler)


class TestMessageParserProtocol:
    """Tests for MessageParser protocol."""

    def test_protocol_check(self) -> None:
        """Test that classes implementing the protocol are recognized."""

        class MyParser:
            def parse(self, payload: dict[str, Any]) -> IncomingMessage | None:
                return None

            def can_parse(self, payload: dict[str, Any]) -> bool:
                return True

        parser = MyParser()
        assert isinstance(parser, MessageParser)

    def test_incomplete_implementation_not_recognized(self) -> None:
        """Test that incomplete implementations are not recognized."""

        class IncompleteParser:
            def parse(self, payload: dict[str, Any]) -> IncomingMessage | None:
                return None

        parser = IncompleteParser()
        assert not isinstance(parser, MessageParser)


class TestGetUserKey:
    """Tests for get_user_key function."""

    def test_group_message(self) -> None:
        """Test user key for group message."""
        msg = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="group",
            chat_id="chat_456",
            sender_id="user_789",
            sender_name="Alice",
            content="Hello",
        )

        key = get_user_key(msg)

        assert key == "feishu:group:user_789"

    def test_private_message(self) -> None:
        """Test user key for private message."""
        msg = IncomingMessage(
            id="msg_123",
            platform="qq",
            chat_type="private",
            chat_id="",
            sender_id="123456789",
            sender_name="Bob",
            content="Hi",
        )

        key = get_user_key(msg)

        assert key == "qq:private:123456789"

    def test_channel_message(self) -> None:
        """Test user key for channel message."""
        msg = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="channel",
            chat_id="channel_001",
            sender_id="user_789",
            sender_name="Alice",
            content="Hello",
        )

        key = get_user_key(msg)

        assert key == "feishu:channel:user_789"


class TestGetChatKey:
    """Tests for get_chat_key function."""

    def test_group_message(self) -> None:
        """Test chat key for group message."""
        msg = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="group",
            chat_id="chat_456",
            sender_id="user_789",
            sender_name="Alice",
            content="Hello",
        )

        key = get_chat_key(msg)

        assert key == "feishu:chat_456"

    def test_private_message_uses_sender_id(self) -> None:
        """Test chat key for private message uses sender_id."""
        msg = IncomingMessage(
            id="msg_123",
            platform="qq",
            chat_type="private",
            chat_id="",
            sender_id="123456789",
            sender_name="Bob",
            content="Hi",
        )

        key = get_chat_key(msg)

        assert key == "qq:123456789"

    def test_channel_message(self) -> None:
        """Test chat key for channel message."""
        msg = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="channel",
            chat_id="channel_001",
            sender_id="user_789",
            sender_name="Alice",
            content="Hello",
        )

        key = get_chat_key(msg)

        assert key == "feishu:channel_001"
