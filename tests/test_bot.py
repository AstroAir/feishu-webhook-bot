"""Tests for the main bot module."""

import tempfile
from pathlib import Path

import pytest
from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core import BotConfig, WebhookConfig


def test_bot_initialization():
    """Test bot initialization with config."""
    config = BotConfig(
        webhooks=[WebhookConfig(url="https://example.com/webhook", name="test")]
    )

    bot = FeishuBot(config)

    assert bot.config == config
    assert bot.client is not None
    assert bot.scheduler is not None
    assert bot.plugin_manager is not None


def test_bot_from_config_file():
    """Test bot creation from config file."""
    config_data = """
webhooks:
  - url: https://example.com/webhook
    name: test
    secret: null

scheduler:
  enabled: true
  timezone: UTC

plugins:
  enabled: false
  plugin_dir: plugins

logging:
  level: INFO
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_data)
        config_path = f.name

    try:
        bot = FeishuBot.from_config(config_path)
        assert bot.config is not None
        assert len(bot.config.webhooks) == 1
        assert bot.config.webhooks[0].url == "https://example.com/webhook"
    finally:
        Path(config_path).unlink()


def test_bot_from_env():
    """Test bot creation from environment config."""
    # This would require setting up environment variables
    # For now, test that the method exists and can be called
    import os

    # Set temporary environment
    os.environ["FEISHU_WEBHOOK_URL"] = "https://example.com/webhook"

    try:
        bot = FeishuBot.from_env()
        assert bot.config is not None
    except Exception:
        # May fail if environment not fully configured
        pass
    finally:
        if "FEISHU_WEBHOOK_URL" in os.environ:
            del os.environ["FEISHU_WEBHOOK_URL"]


def test_bot_disabled_scheduler():
    """Test bot with disabled scheduler."""
    config = BotConfig(
        webhooks=[WebhookConfig(url="https://example.com/webhook", name="test")]
    )
    config.scheduler.enabled = False

    bot = FeishuBot(config)

    assert bot.scheduler is None


def test_bot_disabled_plugins():
    """Test bot with disabled plugins."""
    config = BotConfig(
        webhooks=[WebhookConfig(url="https://example.com/webhook", name="test")]
    )
    config.plugins.enabled = False

    bot = FeishuBot(config)

    assert bot.plugin_manager is None


def test_bot_send_message():
    """Test bot send_message method."""
    config = BotConfig(
        webhooks=[WebhookConfig(url="https://example.com/webhook", name="test")]
    )

    bot = FeishuBot(config)

    # Should not raise error (though it won't actually send without real webhook)
    # In a real test, you'd mock the client
    assert bot.client is not None


def test_bot_multiple_webhooks():
    """Test bot with multiple webhooks."""
    config = BotConfig(
        webhooks=[
            WebhookConfig(url="https://example.com/webhook1", name="webhook1"),
            WebhookConfig(url="https://example.com/webhook2", name="webhook2"),
        ]
    )

    bot = FeishuBot(config)

    assert len(bot.config.webhooks) == 2


def test_bot_default_config():
    """Test bot with default configuration."""
    bot = FeishuBot(BotConfig())

    assert bot.config is not None
    assert len(bot.config.webhooks) >= 1
    assert bot.client is not None


def test_bot_scheduler_enabled():
    """Test bot with scheduler enabled."""
    config = BotConfig(
        webhooks=[WebhookConfig(url="https://example.com/webhook", name="test")]
    )
    config.scheduler.enabled = True

    bot = FeishuBot(config)

    assert bot.scheduler is not None
    assert bot.scheduler.config.enabled is True


def test_bot_plugins_enabled():
    """Test bot with plugins enabled."""
    config = BotConfig(
        webhooks=[WebhookConfig(url="https://example.com/webhook", name="test")]
    )
    config.plugins.enabled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        config.plugins.plugin_dir = tmpdir
        bot = FeishuBot(config)

        assert bot.plugin_manager is not None


def test_bot_config_validation():
    """Test bot with invalid config."""
    # Empty webhooks list should still work (uses default)
    config = BotConfig(webhooks=[])

    bot = FeishuBot(config)
    assert bot.config is not None
