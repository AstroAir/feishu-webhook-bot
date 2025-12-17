"""Tests for the main bot module."""

import asyncio
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core import BotConfig, WebhookConfig


@pytest.fixture
def mock_dependencies(mocker):
    """Fixture to mock all external dependencies of FeishuBot."""
    setup_logging_mock = mocker.patch("feishu_webhook_bot.core.setup_logging")
    mock_client_class = mocker.patch(
        "feishu_webhook_bot.bot.initializers.client_init.FeishuWebhookClient"
    )
    mock_scheduler_class = mocker.patch(
        "feishu_webhook_bot.bot.initializers.scheduler_init.TaskScheduler"
    )
    mock_plugin_manager_class = mocker.patch(
        "feishu_webhook_bot.bot.initializers.plugin_init.PluginManager"
    )

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

    # Verify plugin manager initialization (now includes providers kwarg)
    mock_dependencies["plugin_manager_class"].assert_called_once()
    call_args = mock_dependencies["plugin_manager_class"].call_args
    assert call_args[0][0] == simple_config  # First positional arg is config
    assert "providers" in call_args[1]  # providers is passed as kwarg
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


@patch("feishu_webhook_bot.bot.lifecycle.signal")
def test_start_and_stop_lifecycle(mock_signal, simple_config, mock_dependencies, mocker):
    """Test the start and stop methods of the bot."""
    bot = FeishuBot(simple_config)

    # Mock validate_webhook to return proper tuple
    mock_default_client = cast(MagicMock, bot.clients["default"])
    mock_default_client.validate_webhook.return_value = (True, None)
    mock_default_client.is_configured.return_value = True

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
    with pytest.raises(ValueError, match="Webhook/provider not found: unknown"):
        bot.send_message("test", webhook_name="unknown")


def test_from_config_yaml(mocker):
    """Test creating a bot from a YAML config file."""
    mock_bot_config = mocker.patch("feishu_webhook_bot.bot.main.BotConfig")
    FeishuBot.from_config("config.yaml")
    mock_bot_config.from_yaml.assert_called_once_with(Path("config.yaml"))


def test_from_config_json(mocker):
    """Test creating a bot from a JSON config file."""
    mock_bot_config = mocker.patch("feishu_webhook_bot.bot.main.BotConfig")
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
    mock_bot_config_init = mocker.patch("feishu_webhook_bot.bot.main.BotConfig")

    FeishuBot.from_env()

    # Assert that BotConfig() was called, which triggers pydantic-settings' env loading
    mock_bot_config_init.assert_called_once()


def test_handle_incoming_event_with_ai_chat(simple_config, mock_dependencies, mocker):
    """Test handling incoming chat messages with AI agent."""
    mock_ai_agent = MagicMock()
    bot = FeishuBot(simple_config)
    bot.ai_agent = mock_ai_agent

    # Mock asyncio.create_task to avoid actual async execution
    mock_create_task = mocker.patch("asyncio.create_task")

    payload = {
        "type": "message",
        "event": {"text": "Hello bot", "sender": {"sender_id": {"user_id": "user123"}}},
    }

    bot._handle_incoming_event(payload)

    # Verify AI chat task was created
    mock_create_task.assert_called_once()


def test_handle_incoming_event_with_plugin_manager(simple_config, mock_dependencies):
    """Test that incoming events are dispatched to plugin manager."""
    bot = FeishuBot(simple_config)

    payload = {"type": "test_event", "data": "test"}

    bot._handle_incoming_event(payload)

    mock_dependencies["plugin_manager_instance"].dispatch_event.assert_called_once_with(
        payload, context={}
    )


def test_handle_incoming_event_with_automation_engine(simple_config, mock_dependencies, mocker):
    """Test that incoming events are handled by automation engine."""
    mock_automation_engine = MagicMock()
    mocker.patch(
        "feishu_webhook_bot.bot.initializers.misc_init.AutomationEngine",
        return_value=mock_automation_engine,
    )

    bot = FeishuBot(simple_config)
    bot.automation_engine = mock_automation_engine

    payload = {"type": "test_event"}

    bot._handle_incoming_event(payload)

    mock_automation_engine.handle_event.assert_called_once_with(payload)


def test_is_chat_message_with_type_message(simple_config, mock_dependencies):
    """Test _is_chat_message correctly identifies message events."""
    bot = FeishuBot(simple_config)

    payload = {"type": "message", "text": "Hello"}
    assert bot._is_chat_message(payload) is True


def test_is_chat_message_with_nested_event(simple_config, mock_dependencies):
    """Test _is_chat_message handles nested event structure."""
    bot = FeishuBot(simple_config)

    payload = {"event": {"type": "message"}}
    assert bot._is_chat_message(payload) is True


def test_is_chat_message_with_non_message(simple_config, mock_dependencies):
    """Test _is_chat_message returns False for non-message events."""
    bot = FeishuBot(simple_config)

    payload = {"type": "other_event"}
    assert bot._is_chat_message(payload) is False


def test_handle_ai_chat_success(simple_config, mock_dependencies):
    """Test successful AI chat handling."""
    bot = FeishuBot(simple_config)
    mock_ai_agent = MagicMock()
    mock_ai_agent.chat = AsyncMock(return_value="AI response")
    bot.ai_agent = mock_ai_agent
    bot.chat_controller = None  # Disable chat controller to use legacy handler

    payload = {"event": {"text": "Hello AI", "sender": {"sender_id": {"user_id": "user123"}}}}

    asyncio.run(bot._handle_ai_chat(payload))

    # Verify AI agent was called
    mock_ai_agent.chat.assert_awaited_once_with("user123", "Hello AI")

    # Verify response was sent
    cast(MagicMock, bot.client).send_text.assert_called_once_with("AI response")


def test_handle_ai_chat_empty_message(simple_config, mock_dependencies):
    """Test AI chat handling with empty message."""
    bot = FeishuBot(simple_config)
    mock_ai_agent = MagicMock()
    mock_ai_agent.chat = AsyncMock()
    bot.ai_agent = mock_ai_agent

    payload = {"event": {"text": "", "sender": {"sender_id": {"user_id": "user123"}}}}

    asyncio.run(bot._handle_ai_chat(payload))

    # AI agent should not be called
    mock_ai_agent.chat.assert_not_called()


def test_handle_ai_chat_error_handling(simple_config, mock_dependencies):
    """Test AI chat error handling."""
    bot = FeishuBot(simple_config)
    mock_ai_agent = MagicMock()
    mock_ai_agent.chat = AsyncMock(side_effect=Exception("AI error"))
    bot.ai_agent = mock_ai_agent

    payload = {"event": {"text": "Hello AI", "sender": {"sender_id": {"user_id": "user123"}}}}

    # Should not raise exception
    asyncio.run(bot._handle_ai_chat(payload))


def test_send_rendered_template_text(simple_config, mock_dependencies):
    """Test sending rendered text template."""
    bot = FeishuBot(simple_config)

    from feishu_webhook_bot.core.templates import RenderedTemplate

    rendered = RenderedTemplate(type="text", content="Hello World")

    bot._send_rendered_template(rendered, ["default"])

    cast(MagicMock, bot.client).send_text.assert_called_once_with("Hello World")


def test_send_rendered_template_card(simple_config, mock_dependencies):
    """Test sending rendered card template."""
    bot = FeishuBot(simple_config)

    from feishu_webhook_bot.core.templates import RenderedTemplate

    card_content = {"elements": [{"tag": "div", "text": {"tag": "plain_text", "content": "Test"}}]}
    rendered = RenderedTemplate(type="card", content=card_content)

    bot._send_rendered_template(rendered, ["default"])

    cast(MagicMock, bot.client).send_card.assert_called_once_with(card_content)


def test_send_rendered_template_post(simple_config, mock_dependencies):
    """Test sending rendered post template."""
    bot = FeishuBot(simple_config)

    from feishu_webhook_bot.core.templates import RenderedTemplate

    post_content = {"title": "Test Post", "content": [{"text": "Hello"}], "language": "zh_cn"}
    rendered = RenderedTemplate(type="post", content=post_content)

    bot._send_rendered_template(rendered, ["default"])

    cast(MagicMock, bot.client).send_rich_text.assert_called_once_with(
        "Test Post", [{"text": "Hello"}], language="zh_cn"
    )


def test_send_rendered_template_invalid_webhook(simple_config, mock_dependencies):
    """Test sending rendered template to invalid webhook."""
    bot = FeishuBot(simple_config)

    from feishu_webhook_bot.core.templates import RenderedTemplate

    rendered = RenderedTemplate(type="text", content="Hello")

    with pytest.raises(ValueError, match="Webhook client\\(s\\) not found"):
        bot._send_rendered_template(rendered, ["invalid"])


def test_send_rendered_template_no_webhooks(simple_config, mock_dependencies):
    """Test sending rendered template with no webhook names."""
    bot = FeishuBot(simple_config)

    from feishu_webhook_bot.core.templates import RenderedTemplate

    rendered = RenderedTemplate(type="text", content="Hello")

    with pytest.raises(ValueError, match="No webhook names provided"):
        bot._send_rendered_template(rendered, [])


def test_send_message_multiple_webhooks(mock_dependencies):
    """Test sending message to multiple webhooks."""
    multi_webhook_config = BotConfig(
        webhooks=[
            WebhookConfig(url="https://example.com/webhook1", name="default"),
            WebhookConfig(url="https://example.com/webhook2", name="alerts"),
        ]
    )
    bot = FeishuBot(multi_webhook_config)

    bot.send_message("Test message", webhook_name=["default", "alerts"])

    cast(MagicMock, bot.clients["default"]).send_text.assert_called_once_with("Test message")
    cast(MagicMock, bot.clients["alerts"]).send_text.assert_called_once_with("Test message")


def test_send_message_empty_text(simple_config, mock_dependencies):
    """Test send_message raises error for empty text."""
    bot = FeishuBot(simple_config)

    with pytest.raises(ValueError, match="Message text must be a non-empty string"):
        bot.send_message("")


def test_send_message_empty_webhook_name(simple_config, mock_dependencies):
    """Test send_message raises error for empty webhook name."""
    bot = FeishuBot(simple_config)

    with pytest.raises(ValueError, match="Webhook name must be a non-empty string"):
        bot.send_message("Hello", webhook_name="")


def test_send_message_empty_webhook_list(simple_config, mock_dependencies):
    """Test send_message raises error for empty webhook list."""
    bot = FeishuBot(simple_config)

    with pytest.raises(ValueError, match="At least one webhook name must be provided"):
        bot.send_message("Hello", webhook_name=[])


def test_bot_initialization_with_none_config(mock_dependencies):
    """Test bot initialization raises error with None config."""
    with pytest.raises(ValueError, match="Bot configuration must not be None"):
        FeishuBot(None)


def test_signal_handlers_setup(simple_config, mock_dependencies, mocker):
    """Test signal handlers are properly set up."""
    mock_signal = mocker.patch("feishu_webhook_bot.bot.lifecycle.signal")
    mock_signal.SIGINT = 2
    mock_signal.SIGTERM = 15

    bot = FeishuBot(simple_config)
    bot._setup_signal_handlers()

    assert bot._signal_handlers_installed is True
    assert len(bot._signal_handlers) == 2


def test_signal_handlers_not_reinstalled(simple_config, mock_dependencies, mocker):
    """Test signal handlers are not reinstalled if already installed."""
    mock_signal = mocker.patch("feishu_webhook_bot.bot.lifecycle.signal")

    bot = FeishuBot(simple_config)
    bot._signal_handlers_installed = True
    initial_call_count = mock_signal.signal.call_count

    bot._setup_signal_handlers()

    # Should not call signal.signal again
    assert mock_signal.signal.call_count == initial_call_count


def test_restore_signal_handlers(simple_config, mock_dependencies, mocker):
    """Test signal handlers are properly restored."""
    mock_signal = mocker.patch("feishu_webhook_bot.bot.lifecycle.signal")
    mock_signal.SIGINT = 2
    mock_signal.SIGTERM = 15
    mock_signal.SIG_DFL = 0

    bot = FeishuBot(simple_config)
    bot._signal_handlers = {2: lambda: None, 15: lambda: None}
    bot._signal_handlers_installed = True

    bot._restore_signal_handlers()

    assert bot._signal_handlers_installed is False
    assert len(bot._signal_handlers) == 0


def test_dispatch_rendered_interactive(simple_config, mock_dependencies):
    """Test dispatching interactive card."""
    bot = FeishuBot(simple_config)

    from feishu_webhook_bot.core.templates import RenderedTemplate

    card_content = {"elements": []}
    rendered = RenderedTemplate(type="interactive", content=card_content)

    bot._dispatch_rendered(bot.client, rendered)

    cast(MagicMock, bot.client).send_card.assert_called_once_with(card_content)


def test_dispatch_rendered_fallback(simple_config, mock_dependencies):
    """Test dispatching unknown template type falls back to text."""
    bot = FeishuBot(simple_config)

    from feishu_webhook_bot.core.templates import RenderedTemplate

    rendered = RenderedTemplate(type="unknown", content={"data": "test"})

    bot._dispatch_rendered(bot.client, rendered)

    cast(MagicMock, bot.client).send_text.assert_called_once()


def test_wait_for_shutdown(simple_config, mock_dependencies, mocker):
    """Test _wait_for_shutdown blocks until shutdown event."""
    bot = FeishuBot(simple_config)
    bot._running = True

    # Mock shutdown event to trigger immediately
    mock_event = mocker.MagicMock()
    mock_event.wait.side_effect = [False, True]  # First call returns False, second returns True
    bot._shutdown_event = mock_event

    bot._wait_for_shutdown()

    assert mock_event.wait.call_count == 2
