"""Tests for the core client module."""

import pytest
from feishu_webhook_bot.core import FeishuWebhookClient, WebhookConfig
from feishu_webhook_bot.core.client import CardBuilder


def test_webhook_config_validation():
    """Test webhook config validation."""
    # Valid config
    config = WebhookConfig(url="https://example.com/webhook", name="test")
    assert config.url == "https://example.com/webhook"
    assert config.name == "test"

    # Invalid URL (empty)
    with pytest.raises(ValueError, match="Webhook URL cannot be empty"):
        WebhookConfig(url="", name="test")

    # Invalid URL (no http)
    with pytest.raises(ValueError, match="Webhook URL must start with"):
        WebhookConfig(url="not-a-url", name="test")


def test_card_builder():
    """Test card builder functionality."""
    card = (
        CardBuilder()
        .set_config(wide_screen_mode=True)
        .set_header("Test Title", template="blue", subtitle="Subtitle")
        .add_markdown("**Bold** text")
        .add_text("Plain text")
        .add_divider()
        .add_button("Click Me", url="https://example.com")
        .add_note("Footer note")
        .build()
    )

    assert card["schema"] == "2.0"
    assert card["config"]["wide_screen_mode"] is True
    assert card["header"]["title"]["content"] == "Test Title"
    assert card["header"]["template"] == "blue"
    assert card["header"]["subtitle"]["content"] == "Subtitle"
    assert len(card["elements"]) == 5  # markdown, text, divider, button, note


def test_client_initialization():
    """Test client initialization."""
    config = WebhookConfig(url="https://example.com/webhook", secret="test-secret")
    client = FeishuWebhookClient(config)

    assert client.config == config
    assert client.timeout == 10.0

    client.close()


def test_client_context_manager():
    """Test client as context manager."""
    config = WebhookConfig(url="https://example.com/webhook")

    with FeishuWebhookClient(config) as client:
        assert client.config == config

    # Client should be closed after context
