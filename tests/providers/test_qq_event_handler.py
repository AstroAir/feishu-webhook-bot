"""Tests for providers.qq_event_handler module."""

from __future__ import annotations

import pytest

from feishu_webhook_bot.providers.qq_event_handler import (
    QQEventHandler,
    QQEventMeta,
    QQEventType,
    create_qq_event_handler,
)


class TestQQEventMeta:
    """Tests for QQEventMeta dataclass."""

    def test_create_message_meta(self) -> None:
        """Test creating message event metadata."""
        meta = QQEventMeta(
            post_type="message",
            message_type="group",
            sub_type="normal",
            self_id=123456789,
            time=1704067200,
        )

        assert meta.post_type == "message"
        assert meta.message_type == "group"
        assert meta.sub_type == "normal"
        assert meta.self_id == 123456789

    def test_create_notice_meta(self) -> None:
        """Test creating notice event metadata."""
        meta = QQEventMeta(
            post_type="notice",
            notice_type="group_increase",
        )

        assert meta.post_type == "notice"
        assert meta.notice_type == "group_increase"


class TestQQEventHandler:
    """Tests for QQEventHandler."""

    def test_init_without_bot_qq(self) -> None:
        """Test initializing handler without bot QQ."""
        handler = QQEventHandler()

        assert handler.bot_qq is None

    def test_init_with_bot_qq(self) -> None:
        """Test initializing handler with bot QQ."""
        handler = QQEventHandler(bot_qq="123456789")

        assert handler.bot_qq == "123456789"

    def test_parse_event_meta(self) -> None:
        """Test parsing event metadata."""
        handler = QQEventHandler()
        payload = {
            "post_type": "message",
            "message_type": "group",
            "sub_type": "normal",
            "self_id": 123456789,
            "time": 1704067200,
        }

        meta = handler.parse_event_meta(payload)

        assert meta.post_type == "message"
        assert meta.message_type == "group"
        assert meta.sub_type == "normal"
        assert meta.self_id == 123456789
        assert meta.time == 1704067200

    @pytest.mark.anyio
    async def test_handle_event_message(self) -> None:
        """Test handling message event."""
        handler = QQEventHandler(bot_qq="123456789")
        payload = {
            "post_type": "message",
            "message_type": "group",
            "time": 1704067200,
            "user_id": 987654321,
            "group_id": 111222333,
            "message_id": 12345,
            "message": [{"type": "text", "data": {"text": "Hello"}}],
            "sender": {"nickname": "Alice"},
        }

        msg, notice, request = await handler.handle_event(payload)

        assert msg is not None
        assert notice is None
        assert request is None
        assert msg.platform == "qq"
        assert msg.chat_type == "group"
        assert msg.content == "Hello"

    @pytest.mark.anyio
    async def test_handle_event_notice(self) -> None:
        """Test handling notice event returns QQNoticeEvent."""
        handler = QQEventHandler()
        payload = {
            "post_type": "notice",
            "notice_type": "group_increase",
            "time": 1704067200,
            "group_id": 111222333,
            "user_id": 987654321,
        }

        msg, notice, request = await handler.handle_event(payload)

        assert msg is None
        assert notice is not None
        assert request is None
        assert notice.event_type == QQEventType.NOTICE_GROUP_INCREASE
        assert notice.group_id == 111222333

    @pytest.mark.anyio
    async def test_handle_event_request(self) -> None:
        """Test handling request event returns QQRequestEvent."""
        handler = QQEventHandler()
        payload = {
            "post_type": "request",
            "request_type": "friend",
            "time": 1704067200,
            "user_id": 987654321,
            "flag": "test_flag_123",
            "comment": "Please add me",
        }

        msg, notice, request = await handler.handle_event(payload)

        assert msg is None
        assert notice is None
        assert request is not None
        assert request.event_type == QQEventType.REQUEST_FRIEND
        assert request.user_id == 987654321
        assert request.flag == "test_flag_123"

    @pytest.mark.anyio
    async def test_handle_event_meta_event(self) -> None:
        """Test handling meta event returns all None."""
        handler = QQEventHandler()
        payload = {
            "post_type": "meta_event",
            "meta_event_type": "heartbeat",
        }

        msg, notice, request = await handler.handle_event(payload)

        assert msg is None
        assert notice is None
        assert request is None

    @pytest.mark.anyio
    async def test_handle_event_unknown(self) -> None:
        """Test handling unknown event returns all None."""
        handler = QQEventHandler()
        payload = {
            "post_type": "unknown",
        }

        msg, notice, request = await handler.handle_event(payload)

        assert msg is None
        assert notice is None
        assert request is None

    @pytest.mark.anyio
    async def test_handle_private_message(self) -> None:
        """Test handling private message."""
        handler = QQEventHandler()
        payload = {
            "post_type": "message",
            "message_type": "private",
            "time": 1704067200,
            "user_id": 987654321,
            "message_id": 12345,
            "message": [{"type": "text", "data": {"text": "Hi"}}],
            "sender": {"nickname": "Bob"},
        }

        msg, _, _ = await handler.handle_event(payload)

        assert msg is not None
        assert msg.chat_type == "private"
        assert msg.chat_id == ""

    @pytest.mark.anyio
    async def test_handle_message_event_backward_compat(self) -> None:
        """Test handle_message_event for backward compatibility."""
        handler = QQEventHandler()
        payload = {
            "post_type": "message",
            "message_type": "group",
            "time": 1704067200,
            "user_id": 987654321,
            "group_id": 111222333,
            "message_id": 12345,
            "message": [{"type": "text", "data": {"text": "Test"}}],
            "sender": {"nickname": "Test"},
        }

        msg = await handler.handle_message_event(payload)

        assert msg is not None
        assert msg.content == "Test"

    def test_extract_text_from_segments(self) -> None:
        """Test extracting text from message segments."""
        handler = QQEventHandler()
        message = [
            {"type": "text", "data": {"text": "Hello "}},
            {"type": "at", "data": {"qq": "123456"}},
            {"type": "text", "data": {"text": " world"}},
        ]

        text = handler._extract_text(message)

        assert text == "Hello  world"

    def test_extract_text_from_cq_string(self) -> None:
        """Test extracting text from CQ string."""
        handler = QQEventHandler()
        message = "Hello [CQ:at,qq=123456] world"

        text = handler._extract_text(message)

        assert text == "Hello  world"

    def test_extract_text_from_non_list(self) -> None:
        """Test extracting text from non-list value."""
        handler = QQEventHandler()

        text = handler._extract_text("plain text")

        assert text == "plain text"

    def test_extract_mentions_from_segments(self) -> None:
        """Test extracting mentions from message segments."""
        handler = QQEventHandler()
        message = [
            {"type": "at", "data": {"qq": "123456"}},
            {"type": "at", "data": {"qq": "789012"}},
        ]

        mentions = handler._extract_mentions(message)

        assert "123456" in mentions
        assert "789012" in mentions

    def test_extract_mentions_from_cq_string(self) -> None:
        """Test extracting mentions from CQ string."""
        handler = QQEventHandler()
        message = "[CQ:at,qq=123456] [CQ:at,qq=all]"

        mentions = handler._extract_mentions(message)

        assert "123456" in mentions
        assert "all" in mentions

    def test_extract_mentions_deduplicates(self) -> None:
        """Test that duplicate mentions are removed."""
        handler = QQEventHandler()
        message = [
            {"type": "at", "data": {"qq": "123456"}},
            {"type": "at", "data": {"qq": "123456"}},
        ]

        mentions = handler._extract_mentions(message)

        assert mentions.count("123456") == 1

    def test_is_at_bot_true(self) -> None:
        """Test is_at_bot returns True when bot is mentioned."""
        handler = QQEventHandler(bot_qq="123456789")
        message = [{"type": "at", "data": {"qq": "123456789"}}]

        assert handler._is_at_bot(message) is True

    def test_is_at_bot_with_all(self) -> None:
        """Test is_at_bot returns True for @all."""
        handler = QQEventHandler(bot_qq="123456789")
        message = [{"type": "at", "data": {"qq": "all"}}]

        assert handler._is_at_bot(message) is True

    def test_is_at_bot_false(self) -> None:
        """Test is_at_bot returns False when bot not mentioned."""
        handler = QQEventHandler(bot_qq="123456789")
        message = [{"type": "at", "data": {"qq": "987654321"}}]

        assert handler._is_at_bot(message) is False

    def test_is_at_bot_no_bot_qq(self) -> None:
        """Test is_at_bot returns False when bot_qq not set."""
        handler = QQEventHandler()
        message = [{"type": "at", "data": {"qq": "123456789"}}]

        assert handler._is_at_bot(message) is False

    def test_extract_images(self) -> None:
        """Test extracting images from message."""
        handler = QQEventHandler()
        message = [
            {"type": "image", "data": {"file": "abc.jpg", "url": "https://example.com/abc.jpg"}},
            {"type": "text", "data": {"text": "caption"}},
        ]

        images = handler._extract_images(message)

        assert len(images) == 1
        assert images[0]["file"] == "abc.jpg"
        assert images[0]["url"] == "https://example.com/abc.jpg"

    def test_extract_images_empty(self) -> None:
        """Test extracting images from message without images."""
        handler = QQEventHandler()
        message = [{"type": "text", "data": {"text": "no images"}}]

        images = handler._extract_images(message)

        assert images == []

    def test_strip_at_prefix(self) -> None:
        """Test stripping @bot prefix from content."""
        handler = QQEventHandler(bot_qq="123456789")

        content = handler.strip_at_prefix("@123456789 help")

        assert content == "help"

    def test_strip_at_prefix_with_all(self) -> None:
        """Test stripping @all prefix from content."""
        handler = QQEventHandler(bot_qq="123456789")

        content = handler.strip_at_prefix("@all hello")

        assert content == "hello"

    def test_strip_at_prefix_no_bot_qq(self) -> None:
        """Test strip_at_prefix without bot_qq returns original."""
        handler = QQEventHandler()

        content = handler.strip_at_prefix("@123456789 help")

        assert content == "@123456789 help"


class TestCreateQQEventHandler:
    """Tests for create_qq_event_handler factory function."""

    def test_create_handler(self) -> None:
        """Test factory function."""
        handler = create_qq_event_handler(bot_qq="123456789")

        assert isinstance(handler, QQEventHandler)
        assert handler.bot_qq == "123456789"

    def test_create_handler_without_bot_qq(self) -> None:
        """Test factory function without bot_qq."""
        handler = create_qq_event_handler()

        assert isinstance(handler, QQEventHandler)
        assert handler.bot_qq is None
