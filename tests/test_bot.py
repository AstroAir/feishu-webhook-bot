"""Tests for the main bot module."""

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core import BotConfig, WebhookConfig


@pytest.fixture
def mock_dependencies(mocker):
    """Fixture to mock all external dependencies of FeishuBot."""
    setup_logging_mock = mocker.patch("feishu_webhook_bot.bot.setup_logging")
    mock_client_class = mocker.patch("feishu_webhook_bot.bot.FeishuWebhookClient")
    mock_scheduler_class = mocker.patch("feishu_webhook_bot.bot.TaskScheduler")
    mock_plugin_manager_class = mocker.patch("feishu_webhook_bot.bot.PluginManager")

    # Make instances returned by mocks have the same mock spec
    mock_client_instance = MagicMock()
    mock_scheduler_instance = MagicMock()
    mock_plugin_manager_instance = MagicMock()

    mock_client_class.return_value = mock_client_instance
    mock_scheduler_class.return_value = mock_scheduler_instance
    mock_plugin_manager_class.return_value = mock_plugin_manager_instance

    return {
        "setup_logging": setup_logging_mock,
        "client_class": mock_client_class,
        "scheduler_class": mock_scheduler_class,
        "plugin_manager_class": mock_plugin_manager_class,
        "client_instance": mock_client_instance,
        "scheduler_instance": mock_scheduler_instance,
        "plugin_manager_instance": mock_plugin_manager_instance,
    }


@pytest.fixture
def simple_config():
    """Provides a simple BotConfig with one webhook."""
    return BotConfig(webhooks=[WebhookConfig(url="https://example.com/webhook1", name="default")])


def test_bot_initialization(simple_config, mock_dependencies):
    """Test bot initializes all components correctly."""
    bot = FeishuBot(simple_config)

    # Verify logging is set up
    mock_dependencies["setup_logging"].assert_called_once_with(simple_config.logging)

    # Verify client pooling
    assert "default" in bot.clients
    mock_dependencies["client_class"].assert_called_once_with(simple_config.webhooks[0])
    assert bot.client == bot.clients["default"]

    # Verify scheduler initialization
    mock_dependencies["scheduler_class"].assert_called_once_with(simple_config.scheduler)

    # Verify plugin manager initialization
    mock_dependencies["plugin_manager_class"].assert_called_once_with(
        simple_config, bot.client, bot.scheduler
    )
    mock_dependencies["plugin_manager_instance"].load_plugins.assert_called_once()
    mock_dependencies["plugin_manager_instance"].enable_all.assert_called_once()


def test_bot_initialization_no_webhooks(mock_dependencies):
    """Test bot initialization with no webhooks logs a warning but doesn't fail."""
    config = BotConfig(webhooks=[])
    bot = FeishuBot(config)
    assert not bot.clients
    assert bot.client is None


def test_bot_disabled_components(mock_dependencies):
    """Test that disabled components are not initialized."""
    config = BotConfig(webhooks=[WebhookConfig(url="https://example.com/webhook", name="default")])
    config.scheduler.enabled = False
    config.plugins.enabled = False

    bot = FeishuBot(config)

    assert bot.scheduler is None
    assert bot.plugin_manager is None
    mock_dependencies["scheduler_class"].assert_not_called()
    mock_dependencies["plugin_manager_class"].assert_not_called()


@patch("feishu_webhook_bot.bot.signal")
def test_start_and_stop_lifecycle(mock_signal, simple_config, mock_dependencies, mocker):
    """Test the start and stop methods of the bot."""
    bot = FeishuBot(simple_config)

    # --- Test start ---
    bot.start()

    mock_dependencies["scheduler_instance"].start.assert_called_once()
    mock_dependencies["plugin_manager_instance"].start_hot_reload.assert_called_once()

    # Test startup notification
    mock_default_client = cast(MagicMock, bot.clients["default"])
    mock_default_client.send_text.assert_called_with("🤖 Feishu Bot started successfully!")

    assert bot._running is True
    mock_signal.signal.assert_any_call(mock_signal.SIGINT, mocker.ANY)
    mock_signal.signal.assert_any_call(mock_signal.SIGTERM, mocker.ANY)
    mock_signal.pause.assert_called_once()

    # --- Test stop ---
    bot.stop()

    # Test shutdown notification
    mock_default_client.send_text.assert_called_with("🛑 Feishu Bot is shutting down...")

    mock_dependencies["plugin_manager_instance"].stop_hot_reload.assert_called_once()
    mock_dependencies["plugin_manager_instance"].disable_all.assert_called_once()
    mock_dependencies["scheduler_instance"].shutdown.assert_called_once()

    # Check all clients are closed
    for client_instance in bot.clients.values():
        cast(MagicMock, client_instance).close.assert_called_once()

    assert bot._running is False


def test_send_message_uses_client_pool(simple_config, mock_dependencies):
    """Test that send_message uses the correct client from the pool."""
    multi_webhook_config = BotConfig(
        webhooks=[
            WebhookConfig(url="https://example.com/webhook1", name="default"),
            WebhookConfig(url="https://example.com/webhook2", name="alerts"),
        ]
    )
    bot = FeishuBot(multi_webhook_config)

    # Send to default
    bot.send_message("Hello default", webhook_name="default")
    cast(MagicMock, bot.clients["default"]).send_text.assert_called_once_with("Hello default")
    cast(MagicMock, bot.clients["alerts"]).send_text.assert_not_called()

    # Send to alerts
    bot.send_message("Hello alerts", webhook_name="alerts")
    cast(MagicMock, bot.clients["alerts"]).send_text.assert_called_once_with("Hello alerts")

    # Reset mocks for next assertion
    cast(MagicMock, bot.clients["default"]).send_text.reset_mock()
    cast(MagicMock, bot.clients["alerts"]).send_text.reset_mock()


def test_send_message_invalid_webhook(simple_config, mock_dependencies):
    """Test send_message raises ValueError for an unknown webhook."""
    bot = FeishuBot(simple_config)
    with pytest.raises(ValueError, match="Webhook client not found: unknown"):
        bot.send_message("test", webhook_name="unknown")


def test_from_config_yaml(mocker):
    """Test creating a bot from a YAML config file."""
    mock_bot_config = mocker.patch("feishu_webhook_bot.bot.BotConfig")
    FeishuBot.from_config("config.yaml")
    mock_bot_config.from_yaml.assert_called_once_with(Path("config.yaml"))


def test_from_config_json(mocker):
    """Test creating a bot from a JSON config file."""
    mock_bot_config = mocker.patch("feishu_webhook_bot.bot.BotConfig")
    FeishuBot.from_config("config.json")
    mock_bot_config.from_json.assert_called_once_with(Path("config.json"))


def test_from_config_unsupported_format():
    """Test that from_config raises an error for unsupported file types."""

    with pytest.raises(ValueError, match="Unsupported config file format: .txt"):
        FeishuBot.from_config("config.txt")


def test_from_env(mocker):
    """Test creating a bot from environment variables."""
    # We can't easily test the full env loading here, but we can test that
    # it calls the BotConfig constructor, which is responsible for env loading.
    mock_bot_config_init = mocker.patch("feishu_webhook_bot.bot.BotConfig")

    FeishuBot.from_env()

    # Assert that BotConfig() was called, which triggers pydantic-settings' env loading
    mock_bot_config_init.assert_called_once()
