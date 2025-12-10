"""Tests for configuration module."""

import json

import pytest
import yaml
from pydantic import ValidationError

from feishu_webhook_bot.core import BotConfig, WebhookConfig
from feishu_webhook_bot.core.config import (
    PluginConfig,
    SchedulerConfig,
)


class TestConfigModels:
    """Tests for individual Pydantic config models and their validation."""

    def test_webhook_config_validation(self):
        """Test validation rules within WebhookConfig."""
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            WebhookConfig(url="", name="test")
        with pytest.raises(ValidationError, match="URL must start with http"):
            WebhookConfig(url="example.com", name="test")

    def test_scheduler_config_validation(self):
        """Test validation rules within SchedulerConfig."""
        with pytest.raises(ValidationError, match="job_store_type must be"):
            SchedulerConfig(job_store_type="invalid")

    def test_plugin_config_validation(self):
        """Test validation rules within PluginConfig."""
        with pytest.raises(ValidationError, match="reload_delay must be positive"):
            PluginConfig(reload_delay=0)
        with pytest.raises(ValidationError, match="reload_delay must be positive"):
            PluginConfig(reload_delay=-1.0)


class TestBotConfig:
    """Tests for the main BotConfig class and its functionality."""

    def test_bot_config_defaults(self):
        """Test that BotConfig initializes with sensible defaults."""
        config = BotConfig()
        assert len(config.webhooks) == 1
        assert config.scheduler.enabled is True
        assert config.plugins.enabled is True
        assert config.logging.level == "INFO"
        assert config.general.name == "Feishu Bot"

    def test_get_webhook(self):
        """Test the get_webhook helper method."""
        config = BotConfig(
            webhooks=[
                WebhookConfig(url="https://a.com", name="first"),
                WebhookConfig(url="https://b.com", name="second"),
            ]
        )
        assert config.get_webhook("first").url == "https://a.com"
        assert config.get_webhook("second").url == "https://b.com"
        assert config.get_webhook("nonexistent") is None

    def test_from_yaml(self, tmp_path):
        """Test loading configuration from a YAML file."""
        config_path = tmp_path / "config.yaml"
        config_data = {
            "logging": {"level": "DEBUG"},
            "general": {"name": "My YAML Bot"},
        }
        config_path.write_text(yaml.dump(config_data))

        config = BotConfig.from_yaml(config_path)
        assert config.logging.level == "DEBUG"
        assert config.general.name == "My YAML Bot"

    def test_from_json(self, tmp_path):
        """Test loading configuration from a JSON file."""
        config_path = tmp_path / "config.json"
        config_data = {
            "logging": {"level": "WARNING"},
            "general": {"name": "My JSON Bot"},
        }
        config_path.write_text(json.dumps(config_data))

        config = BotConfig.from_json(config_path)
        assert config.logging.level == "WARNING"
        assert config.general.name == "My JSON Bot"

    def test_from_env(self, monkeypatch):
        """Test loading and overriding configuration from environment variables."""
        monkeypatch.setenv("FEISHU_BOT_LOGGING__LEVEL", "CRITICAL")
        monkeypatch.setenv("FEISHU_BOT_SCHEDULER__ENABLED", "false")
        monkeypatch.setenv("FEISHU_BOT_WEBHOOKS__0__URL", "https://env.example.com")
        monkeypatch.setenv("FEISHU_BOT_WEBHOOKS__0__NAME", "env-webhook")

        # Pydantic-settings reads env vars on initialization
        config = BotConfig()

        assert config.logging.level == "CRITICAL"
        assert config.scheduler.enabled is False
        assert len(config.webhooks) == 1
        assert config.webhooks[0].url == "https://env.example.com"
        assert config.webhooks[0].name == "env-webhook"

    def test_loading_error_handling(self, tmp_path):
        """Test error handling for file loading methods."""
        # File not found
        with pytest.raises(FileNotFoundError):
            BotConfig.from_yaml("nonexistent.yaml")
        with pytest.raises(FileNotFoundError):
            BotConfig.from_json("nonexistent.json")

        # Invalid YAML syntax
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("key: value: nested_value")
        with pytest.raises(ValueError, match="Invalid YAML"):
            BotConfig.from_yaml(invalid_yaml)

        # Invalid JSON syntax
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text('{"key": "value",}')  # trailing comma
        with pytest.raises(ValueError, match="Invalid JSON"):
            BotConfig.from_json(invalid_json)
