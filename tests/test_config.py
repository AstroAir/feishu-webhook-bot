"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest
import yaml
from feishu_webhook_bot.core import BotConfig, WebhookConfig
from feishu_webhook_bot.core.config import LoggingConfig, PluginConfig, SchedulerConfig


def test_webhook_config():
    """Test webhook configuration."""
    config = WebhookConfig(
        url="https://example.com/webhook", secret="test-secret", name="test"
    )

    assert config.url == "https://example.com/webhook"
    assert config.secret == "test-secret"
    assert config.name == "test"


def test_scheduler_config():
    """Test scheduler configuration."""
    config = SchedulerConfig(
        enabled=True, timezone="Asia/Shanghai", job_store_type="memory"
    )

    assert config.enabled is True
    assert config.timezone == "Asia/Shanghai"
    assert config.job_store_type == "memory"


def test_plugin_config():
    """Test plugin configuration."""
    config = PluginConfig(
        enabled=True, plugin_dir="plugins", auto_reload=True, reload_delay=1.0
    )

    assert config.enabled is True
    assert config.plugin_dir == "plugins"
    assert config.auto_reload is True
    assert config.reload_delay == 1.0


def test_logging_config():
    """Test logging configuration."""
    config = LoggingConfig(level="INFO", log_file="logs/bot.log")

    assert config.level == "INFO"
    assert config.log_file == "logs/bot.log"


def test_bot_config_default():
    """Test bot config with defaults."""
    config = BotConfig()

    assert len(config.webhooks) == 1
    assert config.scheduler.enabled is True
    assert config.plugins.enabled is True
    assert config.logging.level == "INFO"


def test_bot_config_from_yaml():
    """Test loading bot config from YAML."""
    config_data = {
        "webhooks": [
            {"url": "https://example.com/webhook", "name": "test", "secret": None}
        ],
        "scheduler": {"enabled": True, "timezone": "UTC"},
        "plugins": {"enabled": True, "plugin_dir": "plugins"},
        "logging": {"level": "DEBUG"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name

    try:
        config = BotConfig.from_yaml(temp_path)

        assert len(config.webhooks) == 1
        assert config.webhooks[0].url == "https://example.com/webhook"
        assert config.scheduler.timezone == "UTC"
        assert config.logging.level == "DEBUG"
    finally:
        Path(temp_path).unlink()


def test_bot_config_get_webhook():
    """Test getting webhook by name."""
    config = BotConfig(
        webhooks=[
            WebhookConfig(url="https://example.com/1", name="first"),
            WebhookConfig(url="https://example.com/2", name="second"),
        ]
    )

    webhook = config.get_webhook("first")
    assert webhook is not None
    assert webhook.url == "https://example.com/1"

    webhook = config.get_webhook("nonexistent")
    assert webhook is None
