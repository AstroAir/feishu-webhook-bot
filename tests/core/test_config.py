"""Comprehensive tests for configuration management module.

Tests cover:
- RetryPolicyConfig validation
- WebhookConfig validation
- SchedulerConfig validation
- PluginConfig validation
- LoggingConfig validation
- BotConfig loading and validation
- Environment variable expansion
- YAML configuration loading
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from feishu_webhook_bot.core.config import (
    AuthConfig,
    BotConfig,
    CircuitBreakerPolicyConfig,
    EventServerConfig,
    GeneralConfig,
    HTTPClientConfig,
    LoggingConfig,
    MessageQueueConfig,
    MessageTrackingConfig,
    PluginConfig,
    PluginSettingsConfig,
    ProviderConfigBase,
    RetryPolicyConfig,
    SchedulerConfig,
    TemplateConfig,
    WebhookConfig,
)

# ==============================================================================
# RetryPolicyConfig Tests
# ==============================================================================


class TestRetryPolicyConfig:
    """Tests for RetryPolicyConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryPolicyConfig()

        assert config.max_attempts == 3
        assert config.backoff_seconds == 1.0
        assert config.backoff_multiplier == 2.0
        assert config.max_backoff_seconds == 30.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryPolicyConfig(
            max_attempts=5,
            backoff_seconds=2.0,
            backoff_multiplier=3.0,
            max_backoff_seconds=60.0,
        )

        assert config.max_attempts == 5
        assert config.backoff_seconds == 2.0

    def test_max_attempts_validation(self):
        """Test max_attempts must be >= 1."""
        with pytest.raises(ValueError):
            RetryPolicyConfig(max_attempts=0)

    def test_backoff_seconds_validation(self):
        """Test backoff_seconds must be >= 0."""
        with pytest.raises(ValueError):
            RetryPolicyConfig(backoff_seconds=-1.0)

    def test_backoff_multiplier_validation(self):
        """Test backoff_multiplier must be >= 1."""
        with pytest.raises(ValueError):
            RetryPolicyConfig(backoff_multiplier=0.5)


# ==============================================================================
# WebhookConfig Tests
# ==============================================================================


class TestWebhookConfig:
    """Tests for WebhookConfig."""

    def test_valid_webhook(self):
        """Test valid webhook configuration."""
        config = WebhookConfig(
            url="https://open.feishu.cn/webhook/123",
            name="test",
        )

        assert config.url == "https://open.feishu.cn/webhook/123"
        assert config.name == "test"

    def test_webhook_with_secret(self):
        """Test webhook with secret."""
        config = WebhookConfig(
            url="https://example.com/webhook",
            secret="my-secret",
        )

        assert config.secret == "my-secret"

    def test_empty_url_raises(self):
        """Test empty URL raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            WebhookConfig(url="")

    def test_invalid_url_raises(self):
        """Test invalid URL raises error."""
        with pytest.raises(ValueError, match="must start with http"):
            WebhookConfig(url="ftp://example.com")

    def test_url_whitespace_stripped(self):
        """Test URL whitespace is stripped."""
        # Note: validator checks startswith("http") before stripping,
        # so leading whitespace will cause validation to fail
        config = WebhookConfig(url="https://example.com/webhook  ")
        assert config.url == "https://example.com/webhook"


# ==============================================================================
# SchedulerConfig Tests
# ==============================================================================


class TestSchedulerConfig:
    """Tests for SchedulerConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SchedulerConfig()

        assert config.enabled is True
        assert config.timezone == "Asia/Shanghai"
        assert config.job_store_type == "memory"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SchedulerConfig(
            enabled=False,
            timezone="UTC",
            job_store_type="sqlite",
            job_store_path="/tmp/jobs.db",
        )

        assert config.enabled is False
        assert config.timezone == "UTC"
        assert config.job_store_type == "sqlite"

    def test_invalid_job_store_type(self):
        """Test invalid job_store_type raises error."""
        with pytest.raises(ValueError, match="memory.*sqlite"):
            SchedulerConfig(job_store_type="redis")


# ==============================================================================
# PluginConfig Tests
# ==============================================================================


class TestPluginConfig:
    """Tests for PluginConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PluginConfig()

        assert config.enabled is True
        assert config.plugin_dir == "plugins"
        assert config.auto_reload is True
        assert config.reload_delay == 1.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = PluginConfig(
            enabled=False,
            plugin_dir="custom_plugins",
            auto_reload=False,
            reload_delay=2.0,
        )

        assert config.enabled is False
        assert config.plugin_dir == "custom_plugins"

    def test_reload_delay_validation(self):
        """Test reload_delay must be positive."""
        with pytest.raises(ValueError, match="positive"):
            PluginConfig(reload_delay=0)

    def test_get_plugin_settings(self):
        """Test getting plugin settings."""
        config = PluginConfig(
            plugin_settings=[
                PluginSettingsConfig(
                    plugin_name="my_plugin",
                    settings={"key": "value"},
                ),
            ],
        )

        settings = config.get_plugin_settings("my_plugin")
        assert settings["key"] == "value"

    def test_get_plugin_settings_not_found(self):
        """Test getting nonexistent plugin settings."""
        config = PluginConfig()

        settings = config.get_plugin_settings("nonexistent")
        assert settings == {}


# ==============================================================================
# LoggingConfig Tests
# ==============================================================================


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.log_file is None
        assert config.max_bytes == 10485760
        assert config.backup_count == 5

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LoggingConfig(
            level="DEBUG",
            log_file="/var/log/bot.log",
            max_bytes=5242880,
            backup_count=3,
        )

        assert config.level == "DEBUG"
        assert config.log_file == "/var/log/bot.log"


# ==============================================================================
# GeneralConfig Tests
# ==============================================================================


class TestGeneralConfig:
    """Tests for GeneralConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GeneralConfig()

        assert config.name == "Feishu Bot"
        assert "bot" in config.description.lower()

    def test_custom_values(self):
        """Test custom configuration values."""
        config = GeneralConfig(
            name="My Custom Bot",
            description="A custom bot for testing.",
        )

        assert config.name == "My Custom Bot"


# ==============================================================================
# HTTPClientConfig Tests
# ==============================================================================


class TestHTTPClientConfig:
    """Tests for HTTPClientConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HTTPClientConfig()

        assert config.timeout == 10.0
        assert config.retry is not None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HTTPClientConfig(
            timeout=30.0,
            retry=RetryPolicyConfig(max_attempts=5),
        )

        assert config.timeout == 30.0
        assert config.retry.max_attempts == 5


# ==============================================================================
# CircuitBreakerPolicyConfig Tests
# ==============================================================================


class TestCircuitBreakerPolicyConfig:
    """Tests for CircuitBreakerPolicyConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CircuitBreakerPolicyConfig()

        assert config.failure_threshold == 5
        assert config.reset_timeout == 30.0
        assert config.half_open_max_calls == 3

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CircuitBreakerPolicyConfig(
            failure_threshold=10,
            reset_timeout=60.0,
            half_open_max_calls=5,
        )

        assert config.failure_threshold == 10


# ==============================================================================
# MessageQueueConfig Tests
# ==============================================================================


class TestMessageQueueConfig:
    """Tests for MessageQueueConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MessageQueueConfig()

        assert config.enabled is False
        assert config.max_batch_size == 10
        assert config.retry_delay == 5.0
        assert config.max_retries == 3

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MessageQueueConfig(
            enabled=True,
            max_batch_size=20,
            retry_delay=10.0,
            max_retries=5,
        )

        assert config.enabled is True
        assert config.max_batch_size == 20


# ==============================================================================
# MessageTrackingConfig Tests
# ==============================================================================


class TestMessageTrackingConfig:
    """Tests for MessageTrackingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MessageTrackingConfig()

        assert config.enabled is False
        assert config.max_history == 10000
        assert config.cleanup_interval == 3600.0
        assert config.db_path is None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MessageTrackingConfig(
            enabled=True,
            max_history=5000,
            db_path="/tmp/messages.db",
        )

        assert config.enabled is True
        assert config.db_path == "/tmp/messages.db"


# ==============================================================================
# EventServerConfig Tests
# ==============================================================================


class TestEventServerConfig:
    """Tests for EventServerConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EventServerConfig()

        assert config.enabled is False
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.path == "/feishu/events"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = EventServerConfig(
            enabled=True,
            host="127.0.0.1",
            port=9000,
            verification_token="token123",
        )

        assert config.enabled is True
        assert config.port == 9000


# ==============================================================================
# AuthConfig Tests
# ==============================================================================


class TestAuthConfig:
    """Tests for AuthConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AuthConfig()

        assert config.enabled is False
        assert config.jwt_algorithm == "HS256"
        assert config.access_token_expire_minutes == 30
        assert config.max_failed_attempts == 5

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AuthConfig(
            enabled=True,
            jwt_secret_key="my-secret-key",
            access_token_expire_minutes=60,
        )

        assert config.enabled is True
        assert config.jwt_secret_key == "my-secret-key"


# ==============================================================================
# ProviderConfigBase Tests
# ==============================================================================


class TestProviderConfigBase:
    """Tests for ProviderConfigBase."""

    def test_feishu_provider(self):
        """Test Feishu provider configuration."""
        config = ProviderConfigBase(
            provider_type="feishu",
            name="feishu_default",
            webhook_url="https://open.feishu.cn/webhook/123",
        )

        assert config.provider_type == "feishu"
        assert config.webhook_url is not None

    def test_feishu_provider_missing_url(self):
        """Test Feishu provider requires webhook_url."""
        with pytest.raises(ValueError, match="webhook_url"):
            ProviderConfigBase(
                provider_type="feishu",
                name="feishu_default",
            )

    def test_napcat_provider(self):
        """Test Napcat provider configuration."""
        config = ProviderConfigBase(
            provider_type="napcat",
            name="qq_default",
            http_url="http://localhost:3000",
        )

        assert config.provider_type == "napcat"
        assert config.http_url is not None

    def test_napcat_provider_missing_url(self):
        """Test Napcat provider requires http_url."""
        with pytest.raises(ValueError, match="http_url"):
            ProviderConfigBase(
                provider_type="napcat",
                name="qq_default",
            )


# ==============================================================================
# TemplateConfig Tests
# ==============================================================================


class TestTemplateConfig:
    """Tests for TemplateConfig."""

    def test_valid_template(self):
        """Test valid template configuration."""
        config = TemplateConfig(
            name="greeting",
            content="Hello, ${name}!",
            type="text",
        )

        assert config.name == "greeting"
        assert config.content == "Hello, ${name}!"

    def test_template_with_engine(self):
        """Test template with engine specification."""
        config = TemplateConfig(
            name="greeting",
            content="Hello, {name}!",
            engine="format",
        )

        assert config.engine == "format"


# ==============================================================================
# BotConfig Tests
# ==============================================================================


class TestBotConfig:
    """Tests for BotConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BotConfig()

        assert len(config.webhooks) == 1
        assert config.scheduler is not None
        assert config.plugins is not None
        assert config.logging is not None

    def test_from_yaml(self):
        """Test loading configuration from YAML."""
        yaml_content = """
webhooks:
  - url: https://example.com/webhook
    name: test
scheduler:
  enabled: true
  timezone: UTC
logging:
  level: DEBUG
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = BotConfig.from_yaml(config_path)

            assert len(config.webhooks) == 1
            assert config.webhooks[0].url == "https://example.com/webhook"
            assert config.scheduler.timezone == "UTC"
            assert config.logging.level == "DEBUG"
        finally:
            Path(config_path).unlink()

    def test_from_yaml_file_not_found(self):
        """Test loading from nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            BotConfig.from_yaml("/nonexistent/config.yaml")

    def test_from_yaml_invalid_yaml(self):
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [")
            config_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                BotConfig.from_yaml(config_path)
        finally:
            Path(config_path).unlink()

    def test_nested_configurations(self):
        """Test nested configuration objects."""
        config = BotConfig(
            webhooks=[
                WebhookConfig(url="https://example.com/webhook"),
            ],
            scheduler=SchedulerConfig(enabled=False),
            plugins=PluginConfig(enabled=False),
            logging=LoggingConfig(level="DEBUG"),
            auth=AuthConfig(enabled=True),
        )

        assert config.scheduler.enabled is False
        assert config.plugins.enabled is False
        assert config.logging.level == "DEBUG"
        assert config.auth.enabled is True


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestConfigIntegration:
    """Integration tests for configuration."""

    def test_full_config_yaml(self):
        """Test loading full configuration from YAML."""
        yaml_content = """
webhooks:
  - url: https://example.com/webhook1
    name: primary
    secret: secret1
  - url: https://example.com/webhook2
    name: secondary

scheduler:
  enabled: true
  timezone: Asia/Shanghai
  job_store_type: memory

plugins:
  enabled: true
  plugin_dir: plugins
  auto_reload: true
  plugin_settings:
    - plugin_name: my_plugin
      enabled: true
      settings:
        key: value

logging:
  level: INFO
  log_file: /var/log/bot.log

general:
  name: Test Bot
  description: A test bot

auth:
  enabled: true
  jwt_secret_key: test-secret

event_server:
  enabled: true
  port: 9000
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = BotConfig.from_yaml(config_path)

            assert len(config.webhooks) == 2
            assert config.webhooks[0].name == "primary"
            assert config.webhooks[0].secret == "secret1"
            assert config.scheduler.enabled is True
            assert config.plugins.get_plugin_settings("my_plugin")["key"] == "value"
            assert config.auth.enabled is True
            assert config.event_server.port == 9000
        finally:
            Path(config_path).unlink()
