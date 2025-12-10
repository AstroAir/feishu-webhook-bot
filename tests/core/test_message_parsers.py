"""Tests for core.message_parsers module."""

from __future__ import annotations

import json
from datetime import datetime

from feishu_webhook_bot.core.message_parsers import (
    FeishuMessageParser,
    QQMessageParser,
    create_feishu_parser,
    create_qq_parser,
)


class TestFeishuMessageParser:
    """Tests for FeishuMessageParser."""

    def test_can_parse_v2_message_event(self) -> None:
        """Test can_parse returns True for v2 message events."""
        parser = FeishuMessageParser()
        payload = {
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
            },
        }

        assert parser.can_parse(payload) is True

    def test_can_parse_v1_message_event(self) -> None:
        """Test can_parse returns True for v1 message events."""
        parser = FeishuMessageParser()
        payload = {"type": "message"}

        assert parser.can_parse(payload) is True

    def test_can_parse_returns_false_for_non_message(self) -> None:
        """Test can_parse returns False for non-message events."""
        parser = FeishuMessageParser()
        payload = {
            "header": {
                "event_type": "im.chat.member.user.added_v1",
            },
        }

        assert parser.can_parse(payload) is False

    def test_parse_v2_group_message(self) -> None:
        """Test parsing v2 group message event."""
        parser = FeishuMessageParser(bot_open_id="ou_bot_123")
        payload = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_123",
                "event_type": "im.message.receive_v1",
                "create_time": "1704067200000",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_user_456"},
                    "sender_type": "user",
                },
                "message": {
                    "message_id": "om_msg_789",
                    "chat_id": "oc_chat_001",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "Hello @bot"}),
                    "mentions": [
                        {"key": "@_user_1", "id": {"open_id": "ou_bot_123"}}
                    ],
                },
            },
        }

        msg = parser.parse(payload)

        assert msg is not None
        assert msg.id == "om_msg_789"
        assert msg.platform == "feishu"
        assert msg.chat_type == "group"
        assert msg.chat_id == "oc_chat_001"
        assert msg.sender_id == "ou_user_456"
        assert msg.content == "Hello @bot"
        assert msg.is_at_bot is True
        assert "ou_bot_123" in msg.mentions

    def test_parse_v2_private_message(self) -> None:
        """Test parsing v2 private (p2p) message event."""
        parser = FeishuMessageParser()
        payload = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_123",
                "event_type": "im.message.receive_v1",
                "create_time": "1704067200000",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_user_456"},
                    "sender_type": "user",
                },
                "message": {
                    "message_id": "om_msg_789",
                    "chat_id": "",
                    "chat_type": "p2p",
                    "message_type": "text",
                    "content": json.dumps({"text": "Hello"}),
                },
            },
        }

        msg = parser.parse(payload)

        assert msg is not None
        assert msg.chat_type == "private"
        assert msg.chat_id == ""

    def test_parse_v1_message(self) -> None:
        """Test parsing v1 legacy message event."""
        parser = FeishuMessageParser()
        payload = {
            "type": "message",
            "event": {
                "message_id": "om_msg_123",
                "chat_id": "oc_chat_001",
                "chat_type": "group",
                "open_id": "ou_user_456",
                "user_name": "Alice",
                "text": "Hello world",
                "is_mention": False,
            },
        }

        msg = parser.parse(payload)

        assert msg is not None
        assert msg.id == "om_msg_123"
        assert msg.platform == "feishu"
        assert msg.sender_id == "ou_user_456"
        assert msg.sender_name == "Alice"
        assert msg.content == "Hello world"

    def test_parse_returns_none_for_non_message(self) -> None:
        """Test parse returns None for non-message events."""
        parser = FeishuMessageParser()
        payload = {
            "header": {
                "event_type": "im.chat.member.user.added_v1",
            },
        }

        msg = parser.parse(payload)

        assert msg is None

    def test_parse_post_message(self) -> None:
        """Test parsing rich text (post) message."""
        parser = FeishuMessageParser()
        post_content = {
            "zh_cn": {
                "title": "Title",
                "content": [
                    [
                        {"tag": "text", "text": "Hello "},
                        {"tag": "at", "user_name": "Bob"},
                    ]
                ],
            }
        }
        payload = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_123",
                "event_type": "im.message.receive_v1",
                "create_time": "1704067200000",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_user_456"},
                },
                "message": {
                    "message_id": "om_msg_789",
                    "chat_id": "oc_chat_001",
                    "chat_type": "group",
                    "message_type": "post",
                    "content": json.dumps(post_content),
                },
            },
        }

        msg = parser.parse(payload)

        assert msg is not None
        assert "Hello" in msg.content
        assert "@Bob" in msg.content

    def test_parse_with_thread_info(self) -> None:
        """Test parsing message with thread/reply info."""
        parser = FeishuMessageParser()
        payload = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_123",
                "event_type": "im.message.receive_v1",
                "create_time": "1704067200000",
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_user_456"},
                },
                "message": {
                    "message_id": "om_msg_789",
                    "root_id": "om_root_001",
                    "parent_id": "om_parent_002",
                    "chat_id": "oc_chat_001",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": json.dumps({"text": "Reply"}),
                },
            },
        }

        msg = parser.parse(payload)

        assert msg is not None
        assert msg.thread_id == "om_root_001"
        assert msg.reply_to == "om_parent_002"

    def test_map_chat_type(self) -> None:
        """Test chat type mapping."""
        parser = FeishuMessageParser()

        assert parser._map_chat_type("p2p") == "private"
        assert parser._map_chat_type("private") == "private"
        assert parser._map_chat_type("group") == "group"
        assert parser._map_chat_type("topic") == "channel"
        assert parser._map_chat_type("unknown") == "group"

    def test_parse_timestamp_milliseconds(self) -> None:
        """Test parsing millisecond timestamp."""
        parser = FeishuMessageParser()

        result = parser._parse_timestamp("1704067200000")

        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_parse_timestamp_empty(self) -> None:
        """Test parsing empty timestamp returns now."""
        parser = FeishuMessageParser()

        result = parser._parse_timestamp("")

        assert isinstance(result, datetime)


class TestQQMessageParser:
    """Tests for QQMessageParser."""

    def test_can_parse_message_event(self) -> None:
        """Test can_parse returns True for message events."""
        parser = QQMessageParser()
        payload = {"post_type": "message"}

        assert parser.can_parse(payload) is True

    def test_can_parse_returns_false_for_non_message(self) -> None:
        """Test can_parse returns False for non-message events."""
        parser = QQMessageParser()
        payload = {"post_type": "notice"}

        assert parser.can_parse(payload) is False

    def test_parse_group_message(self) -> None:
        """Test parsing group message event."""
        parser = QQMessageParser(bot_qq="123456789")
        payload = {
            "post_type": "message",
            "message_type": "group",
            "time": 1704067200,
            "self_id": 123456789,
            "user_id": 987654321,
            "group_id": 111222333,
            "message_id": 12345,
            "message": [
                {"type": "text", "data": {"text": "Hello "}},
                {"type": "at", "data": {"qq": "123456789"}},
            ],
            "raw_message": "Hello [CQ:at,qq=123456789]",
            "sender": {
                "user_id": 987654321,
                "nickname": "Alice",
                "card": "Alice in Wonderland",
            },
        }

        msg = parser.parse(payload)

        assert msg is not None
        assert msg.id == "12345"
        assert msg.platform == "qq"
        assert msg.chat_type == "group"
        assert msg.chat_id == "111222333"
        assert msg.sender_id == "987654321"
        assert msg.sender_name == "Alice in Wonderland"
        assert msg.content == "Hello"
        assert msg.is_at_bot is True
        assert "123456789" in msg.mentions

    def test_parse_private_message(self) -> None:
        """Test parsing private message event."""
        parser = QQMessageParser()
        payload = {
            "post_type": "message",
            "message_type": "private",
            "time": 1704067200,
            "user_id": 987654321,
            "message_id": 12345,
            "message": [{"type": "text", "data": {"text": "Hello"}}],
            "sender": {
                "user_id": 987654321,
                "nickname": "Bob",
            },
        }

        msg = parser.parse(payload)

        assert msg is not None
        assert msg.chat_type == "private"
        assert msg.chat_id == ""
        assert msg.sender_name == "Bob"

    def test_parse_returns_none_for_non_message(self) -> None:
        """Test parse returns None for non-message events."""
        parser = QQMessageParser()
        payload = {"post_type": "notice"}

        msg = parser.parse(payload)

        assert msg is None

    def test_extract_text_from_segments(self) -> None:
        """Test extracting text from message segments."""
        parser = QQMessageParser()
        message = [
            {"type": "text", "data": {"text": "Hello "}},
            {"type": "at", "data": {"qq": "123456"}},
            {"type": "text", "data": {"text": " world"}},
        ]

        text = parser._extract_text(message)

        assert text == "Hello  world"

    def test_extract_text_from_cq_string(self) -> None:
        """Test extracting text from CQ string."""
        parser = QQMessageParser()
        message = "Hello [CQ:at,qq=123456] world"

        text = parser._extract_text(message)

        assert text == "Hello  world"

    def test_extract_mentions_from_segments(self) -> None:
        """Test extracting mentions from message segments."""
        parser = QQMessageParser()
        message = [
            {"type": "at", "data": {"qq": "123456"}},
            {"type": "at", "data": {"qq": "789012"}},
        ]

        mentions = parser._extract_mentions(message)

        assert "123456" in mentions
        assert "789012" in mentions

    def test_extract_mentions_from_cq_string(self) -> None:
        """Test extracting mentions from CQ string."""
        parser = QQMessageParser()
        message = "[CQ:at,qq=123456] [CQ:at,qq=all]"

        mentions = parser._extract_mentions(message)

        assert "123456" in mentions
        assert "all" in mentions

    def test_is_at_bot_with_specific_mention(self) -> None:
        """Test is_at_bot with specific bot mention."""
        parser = QQMessageParser(bot_qq="123456789")
        message = [{"type": "at", "data": {"qq": "123456789"}}]

        assert parser._is_at_bot(message) is True

    def test_is_at_bot_with_all_mention(self) -> None:
        """Test is_at_bot with @all mention."""
        parser = QQMessageParser(bot_qq="123456789")
        message = [{"type": "at", "data": {"qq": "all"}}]

        assert parser._is_at_bot(message) is True

    def test_is_at_bot_without_bot_qq(self) -> None:
        """Test is_at_bot returns False when bot_qq not set."""
        parser = QQMessageParser()
        message = [{"type": "at", "data": {"qq": "123456789"}}]

        assert parser._is_at_bot(message) is False


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_feishu_parser(self) -> None:
        """Test create_feishu_parser factory function."""
        parser = create_feishu_parser(bot_open_id="ou_bot_123")

        assert isinstance(parser, FeishuMessageParser)
        assert parser.bot_open_id == "ou_bot_123"

    def test_create_feishu_parser_without_bot_id(self) -> None:
        """Test create_feishu_parser without bot_open_id."""
        parser = create_feishu_parser()

        assert isinstance(parser, FeishuMessageParser)
        assert parser.bot_open_id is None

    def test_create_qq_parser(self) -> None:
        """Test create_qq_parser factory function."""
        parser = create_qq_parser(bot_qq="123456789")

        assert isinstance(parser, QQMessageParser)
        assert parser.bot_qq == "123456789"

    def test_create_qq_parser_without_bot_qq(self) -> None:
        """Test create_qq_parser without bot_qq."""
        parser = create_qq_parser()

        assert isinstance(parser, QQMessageParser)
        assert parser.bot_qq is None
