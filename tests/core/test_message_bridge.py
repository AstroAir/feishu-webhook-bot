"""Tests for the message bridge engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from feishu_webhook_bot.core.config import (
    MessageBridgeConfig,
    MessageBridgeRuleConfig,
)
from feishu_webhook_bot.core.message_bridge import (
    BridgeStatistics,
    MessageBridgeEngine,
    RateLimiter,
)


@dataclass
class MockIncomingMessage:
    """Mock incoming message for testing."""

    platform: str = "qq"
    chat_type: str = "group"
    chat_id: str = "123456"
    sender_id: str = "user123"
    sender_name: str = "TestUser"
    content: str = "Hello, world!"
    raw_data: dict[str, Any] | None = None


class MockProvider:
    """Mock message provider for testing."""

    def __init__(self, name: str = "mock_provider"):
        self.name = name
        self.sent_messages: list[tuple[str, str | None]] = []
        self.should_fail = False

    def send_text(self, text: str, target: str | None = None) -> MagicMock:
        """Mock send_text method."""
        if self.should_fail:
            raise Exception("Mock send failure")
        self.sent_messages.append((text, target))
        result = MagicMock()
        result.success = True
        result.message_id = "msg_123"
        return result


class TestBridgeStatistics:
    """Tests for BridgeStatistics."""

    def test_initial_state(self):
        """Test initial statistics state."""
        stats = BridgeStatistics()
        assert stats.total_forwarded == 0
        assert stats.total_failed == 0
        assert stats.total_filtered == 0
        assert stats.last_forward_time is None

    def test_record_forward(self):
        """Test recording a successful forward."""
        stats = BridgeStatistics()
        stats.record_forward("rule1")

        assert stats.total_forwarded == 1
        assert stats.by_rule["rule1"]["forwarded"] == 1
        assert stats.last_forward_time is not None

    def test_record_failure(self):
        """Test recording a failed forward."""
        stats = BridgeStatistics()
        stats.record_failure("rule1")

        assert stats.total_failed == 1
        assert stats.by_rule["rule1"]["failed"] == 1

    def test_record_filtered(self):
        """Test recording a filtered message."""
        stats = BridgeStatistics()
        stats.record_filtered("rule1")

        assert stats.total_filtered == 1
        assert stats.by_rule["rule1"]["filtered"] == 1

    def test_to_dict(self):
        """Test converting statistics to dictionary."""
        stats = BridgeStatistics()
        stats.record_forward("rule1")
        stats.record_failure("rule2")

        result = stats.to_dict()

        assert result["total_forwarded"] == 1
        assert result["total_failed"] == 1
        assert "uptime_seconds" in result
        assert result["last_forward_time"] is not None


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_allows_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = RateLimiter(max_per_minute=10)

        for _ in range(10):
            assert limiter.is_allowed("rule1") is True

    def test_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(max_per_minute=5)

        for _ in range(5):
            limiter.is_allowed("rule1")

        assert limiter.is_allowed("rule1") is False

    def test_separate_rules(self):
        """Test that different rules have separate limits."""
        limiter = RateLimiter(max_per_minute=2)

        assert limiter.is_allowed("rule1") is True
        assert limiter.is_allowed("rule1") is True
        assert limiter.is_allowed("rule1") is False

        # Different rule should still be allowed
        assert limiter.is_allowed("rule2") is True

    def test_get_remaining(self):
        """Test getting remaining allowed messages."""
        limiter = RateLimiter(max_per_minute=10)

        assert limiter.get_remaining("rule1") == 10

        limiter.is_allowed("rule1")
        limiter.is_allowed("rule1")

        assert limiter.get_remaining("rule1") == 8


class TestMessageBridgeEngine:
    """Tests for MessageBridgeEngine."""

    @pytest.fixture
    def basic_config(self) -> MessageBridgeConfig:
        """Create a basic bridge configuration."""
        return MessageBridgeConfig(
            enabled=True,
            rules=[
                MessageBridgeRuleConfig(
                    name="qq_to_feishu",
                    enabled=True,
                    source_provider="qq_main",
                    source_chat_type="all",
                    target_provider="feishu_default",
                    target_chat_id="webhook_url",
                ),
            ],
            default_format="[{source}] {sender}: {content}",
            rate_limit_per_minute=60,
        )

    @pytest.fixture
    def providers(self) -> dict[str, MockProvider]:
        """Create mock providers."""
        return {
            "qq_main": MockProvider("qq_main"),
            "feishu_default": MockProvider("feishu_default"),
        }

    def test_initialization(self, basic_config, providers):
        """Test engine initialization."""
        engine = MessageBridgeEngine(basic_config, providers)

        assert engine.config == basic_config
        assert len(engine.providers) == 2
        assert not engine.is_running()

    def test_start_stop(self, basic_config, providers):
        """Test starting and stopping the engine."""
        engine = MessageBridgeEngine(basic_config, providers)

        engine.start()
        assert engine.is_running()

        engine.stop()
        assert not engine.is_running()

    def test_disabled_config(self, providers):
        """Test that disabled config doesn't start."""
        config = MessageBridgeConfig(enabled=False, rules=[])
        engine = MessageBridgeEngine(config, providers)

        engine.start()
        assert not engine.is_running()

    def test_list_rules(self, basic_config, providers):
        """Test listing rules."""
        engine = MessageBridgeEngine(basic_config, providers)
        rules = engine.list_rules()

        assert len(rules) == 1
        assert rules[0]["name"] == "qq_to_feishu"
        assert rules[0]["enabled"] is True

    def test_enable_disable_rule(self, basic_config, providers):
        """Test enabling and disabling rules."""
        engine = MessageBridgeEngine(basic_config, providers)

        # Disable rule
        result = engine.disable_rule("qq_to_feishu")
        assert result is True
        assert basic_config.rules[0].enabled is False

        # Enable rule
        result = engine.enable_rule("qq_to_feishu")
        assert result is True
        assert basic_config.rules[0].enabled is True

        # Non-existent rule
        result = engine.disable_rule("non_existent")
        assert result is False

    def test_get_rule_status(self, basic_config, providers):
        """Test getting rule status."""
        engine = MessageBridgeEngine(basic_config, providers)

        status = engine.get_rule_status("qq_to_feishu")
        assert status is not None
        assert status["name"] == "qq_to_feishu"
        assert status["enabled"] is True

        # Non-existent rule
        status = engine.get_rule_status("non_existent")
        assert status is None

    def test_get_statistics(self, basic_config, providers):
        """Test getting statistics."""
        engine = MessageBridgeEngine(basic_config, providers)
        stats = engine.get_statistics()

        assert stats["total_forwarded"] == 0
        assert stats["total_failed"] == 0
        assert "uptime_seconds" in stats


class TestMessageBridgeFiltering:
    """Tests for message filtering in bridge engine."""

    @pytest.fixture
    def filter_config(self) -> MessageBridgeConfig:
        """Create a config with filtering rules."""
        return MessageBridgeConfig(
            enabled=True,
            rules=[
                MessageBridgeRuleConfig(
                    name="filtered_rule",
                    enabled=True,
                    source_provider="qq_main",
                    source_chat_type="group",
                    source_chat_ids=["123456"],
                    target_provider="feishu_default",
                    target_chat_id="webhook",
                    keyword_whitelist=["important"],
                    keyword_blacklist=["spam"],
                    sender_whitelist=["user123"],
                    sender_blacklist=["blocked_user"],
                ),
            ],
        )

    @pytest.fixture
    def providers(self) -> dict[str, MockProvider]:
        """Create mock providers."""
        return {
            "qq_main": MockProvider("qq_main"),
            "feishu_default": MockProvider("feishu_default"),
        }

    def test_keyword_whitelist_pass(self, filter_config, providers):
        """Test message passes keyword whitelist."""
        engine = MessageBridgeEngine(filter_config, providers)
        rule = filter_config.rules[0]
        message = MockIncomingMessage(content="This is important message")

        result = engine._check_keyword_filter(rule, message)
        assert result is True

    def test_keyword_whitelist_fail(self, filter_config, providers):
        """Test message fails keyword whitelist."""
        engine = MessageBridgeEngine(filter_config, providers)
        rule = filter_config.rules[0]
        message = MockIncomingMessage(content="Regular message")

        result = engine._check_keyword_filter(rule, message)
        assert result is False

    def test_keyword_blacklist(self, filter_config, providers):
        """Test message blocked by keyword blacklist."""
        engine = MessageBridgeEngine(filter_config, providers)
        rule = filter_config.rules[0]
        message = MockIncomingMessage(content="This is spam important")

        result = engine._check_keyword_filter(rule, message)
        assert result is False

    def test_sender_whitelist_pass(self, filter_config, providers):
        """Test message passes sender whitelist."""
        engine = MessageBridgeEngine(filter_config, providers)
        rule = filter_config.rules[0]
        message = MockIncomingMessage(sender_id="user123")

        result = engine._check_sender_filter(rule, message)
        assert result is True

    def test_sender_whitelist_fail(self, filter_config, providers):
        """Test message fails sender whitelist."""
        engine = MessageBridgeEngine(filter_config, providers)
        rule = filter_config.rules[0]
        message = MockIncomingMessage(sender_id="other_user")

        result = engine._check_sender_filter(rule, message)
        assert result is False

    def test_sender_blacklist(self, filter_config, providers):
        """Test message blocked by sender blacklist."""
        engine = MessageBridgeEngine(filter_config, providers)
        # Modify rule to only have blacklist
        rule = filter_config.rules[0]
        rule.sender_whitelist = []
        message = MockIncomingMessage(sender_id="blocked_user")

        result = engine._check_sender_filter(rule, message)
        assert result is False


class TestMessageTransformation:
    """Tests for message transformation."""

    @pytest.fixture
    def transform_config(self) -> MessageBridgeConfig:
        """Create a config with transformation settings."""
        return MessageBridgeConfig(
            enabled=True,
            rules=[
                MessageBridgeRuleConfig(
                    name="transform_rule",
                    enabled=True,
                    source_provider="qq_main",
                    target_provider="feishu_default",
                    target_chat_id="webhook",
                    include_sender_info=True,
                    message_prefix="[转发] ",
                    message_suffix=" [END]",
                ),
            ],
            default_format="[{source}] {sender}: {content}",
        )

    @pytest.fixture
    def providers(self) -> dict[str, MockProvider]:
        """Create mock providers."""
        return {
            "qq_main": MockProvider("qq_main"),
            "feishu_default": MockProvider("feishu_default"),
        }

    def test_transform_with_sender_info(self, transform_config, providers):
        """Test transformation with sender info included."""
        engine = MessageBridgeEngine(transform_config, providers)
        rule = transform_config.rules[0]
        message = MockIncomingMessage(
            platform="qq",
            sender_name="TestUser",
            content="Hello!",
        )

        result = engine._transform_message(rule, message)

        assert "[Qq] TestUser: Hello!" in result
        assert result.startswith("[转发] ")
        assert result.endswith(" [END]")

    def test_transform_without_sender_info(self, transform_config, providers):
        """Test transformation without sender info."""
        engine = MessageBridgeEngine(transform_config, providers)
        rule = transform_config.rules[0]
        rule.include_sender_info = False
        message = MockIncomingMessage(content="Hello!")

        result = engine._transform_message(rule, message)

        assert result == "[转发] Hello! [END]"


class TestAsyncMessageHandling:
    """Tests for async message handling."""

    @pytest.fixture
    def basic_config(self) -> MessageBridgeConfig:
        """Create a basic bridge configuration."""
        return MessageBridgeConfig(
            enabled=True,
            rules=[
                MessageBridgeRuleConfig(
                    name="test_rule",
                    enabled=True,
                    source_provider="qq_main",
                    source_chat_type="all",
                    target_provider="feishu_default",
                    target_chat_id="webhook",
                ),
            ],
        )

    @pytest.fixture
    def providers(self) -> dict[str, MockProvider]:
        """Create mock providers."""
        return {
            "qq_main": MockProvider("qq_main"),
            "feishu_default": MockProvider("feishu_default"),
        }

    @pytest.mark.asyncio
    async def test_handle_message_not_running(self, basic_config, providers):
        """Test handling message when engine is not running."""
        engine = MessageBridgeEngine(basic_config, providers)
        message = MockIncomingMessage()

        results = await engine.handle_message(message)

        assert results == []

    @pytest.mark.asyncio
    async def test_forward_message_success(self, basic_config, providers):
        """Test successful message forwarding."""
        engine = MessageBridgeEngine(basic_config, providers)
        rule = basic_config.rules[0]

        success = await engine._forward_message(rule, "Test content")

        assert success is True
        assert len(providers["feishu_default"].sent_messages) == 1
        assert providers["feishu_default"].sent_messages[0] == ("Test content", "webhook")

    @pytest.mark.asyncio
    async def test_forward_message_failure(self, basic_config, providers):
        """Test message forwarding failure."""
        engine = MessageBridgeEngine(basic_config, providers)
        engine.config.retry_on_failure = False
        rule = basic_config.rules[0]
        providers["feishu_default"].should_fail = True

        success = await engine._forward_message(rule, "Test content")

        assert success is False
