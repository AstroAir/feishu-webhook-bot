"""Tests for plugin configuration."""

import pytest

from feishu_webhook_bot.core.config import BotConfig, PluginConfig

from tests.mocks import MockPlugin


@pytest.fixture
def mock_config():
    """Create a mock bot configuration with plugin settings."""
    return BotConfig(
        webhooks=[
            {"name": "default", "url": "https://example.com/webhook"},
        ],
        plugins=PluginConfig(
            enabled=True,
            plugin_dir="plugins",
            plugin_settings=[
                {
                    "plugin_name": "test-plugin",
                    "enabled": True,
                    "priority": 10,
                    "settings": {
                        "api_key": "test-key-123",
                        "threshold": 80,
                        "check_interval": 300,
                        "enable_alerts": True,
                    },
                },
                {
                    "plugin_name": "another-plugin",
                    "enabled": True,
                    "priority": 50,
                    "settings": {
                        "custom_setting": "value",
                        "timeout": 30,
                    },
                },
                {
                    "plugin_name": "disabled-plugin",
                    "enabled": False,
                    "priority": 100,
                    "settings": {
                        "some_setting": "value",
                    },
                },
            ],
        ),
    )


@pytest.fixture
def mock_plugin(mock_config):
    """Create a mock plugin instance."""
    from feishu_webhook_bot.core.client import FeishuWebhookClient
    from feishu_webhook_bot.core.config import WebhookConfig

    webhook_config = WebhookConfig(url="https://example.com/webhook", name="test")
    client = FeishuWebhookClient(config=webhook_config)
    return MockPlugin(config=mock_config, client=client)


class TestPluginSettingsRetrieval:
    """Test plugin settings retrieval."""

    def test_get_plugin_settings(self, mock_config):
        """Test getting plugin settings by name."""
        settings = mock_config.plugins.get_plugin_settings("test-plugin")

        assert settings is not None
        assert settings["api_key"] == "test-key-123"
        assert settings["threshold"] == 80
        assert settings["check_interval"] == 300
        assert settings["enable_alerts"] is True

    def test_get_settings_for_nonexistent_plugin(self, mock_config):
        """Test getting settings for a plugin that doesn't exist."""
        settings = mock_config.plugins.get_plugin_settings("nonexistent")

        assert settings == {}

    def test_get_settings_for_multiple_plugins(self, mock_config):
        """Test getting settings for multiple plugins."""
        test_settings = mock_config.plugins.get_plugin_settings("test-plugin")
        another_settings = mock_config.plugins.get_plugin_settings("another-plugin")

        assert test_settings["api_key"] == "test-key-123"
        assert another_settings["custom_setting"] == "value"


class TestPluginConfigAccess:
    """Test plugin configuration access methods."""

    def test_get_config_value(self, mock_plugin):
        """Test getting a specific config value."""
        value = mock_plugin.get_config_value("api_key")

        assert value == "test-key-123"

    def test_get_config_value_with_default(self, mock_plugin):
        """Test getting a config value with default."""
        value = mock_plugin.get_config_value("nonexistent_key", default="default_value")

        assert value == "default_value"

    def test_get_config_value_missing_no_default(self, mock_plugin):
        """Test getting a missing config value without default."""
        value = mock_plugin.get_config_value("nonexistent_key")

        assert value is None

    def test_get_all_config(self, mock_plugin):
        """Test getting all config values."""
        all_config = mock_plugin.get_all_config()

        assert all_config is not None
        assert all_config["api_key"] == "test-key-123"
        assert all_config["threshold"] == 80
        assert all_config["check_interval"] == 300
        assert all_config["enable_alerts"] is True

    def test_get_config_different_types(self, mock_plugin):
        """Test getting config values of different types."""
        api_key = mock_plugin.get_config_value("api_key")  # string
        threshold = mock_plugin.get_config_value("threshold")  # int
        enable_alerts = mock_plugin.get_config_value("enable_alerts")  # bool

        assert isinstance(api_key, str)
        assert isinstance(threshold, int)
        assert isinstance(enable_alerts, bool)


class TestPluginPriority:
    """Test plugin loading priority."""

    def test_plugin_settings_have_priority(self, mock_config):
        """Test that plugin settings include priority."""
        for plugin_setting in mock_config.plugins.plugin_settings:
            assert hasattr(plugin_setting, "priority")
            assert isinstance(plugin_setting.priority, int)

    def test_plugins_sorted_by_priority(self, mock_config):
        """Test that plugins can be sorted by priority."""
        sorted_settings = sorted(
            mock_config.plugins.plugin_settings,
            key=lambda x: x.priority,
        )

        priorities = [s.priority for s in sorted_settings]
        assert priorities == [10, 50, 100]
        assert sorted_settings[0].plugin_name == "test-plugin"
        assert sorted_settings[1].plugin_name == "another-plugin"
        assert sorted_settings[2].plugin_name == "disabled-plugin"


class TestPluginEnableDisable:
    """Test plugin enable/disable via configuration."""

    def test_plugin_enabled_flag(self, mock_config):
        """Test checking if a plugin is enabled."""
        test_plugin_setting = next(
            s for s in mock_config.plugins.plugin_settings if s.plugin_name == "test-plugin"
        )
        disabled_plugin_setting = next(
            s for s in mock_config.plugins.plugin_settings if s.plugin_name == "disabled-plugin"
        )

        assert test_plugin_setting.enabled is True
        assert disabled_plugin_setting.enabled is False

    def test_get_enabled_plugins(self, mock_config):
        """Test getting only enabled plugins."""
        enabled_plugins = [s for s in mock_config.plugins.plugin_settings if s.enabled]

        assert len(enabled_plugins) == 2
        plugin_names = [s.plugin_name for s in enabled_plugins]
        assert "test-plugin" in plugin_names
        assert "another-plugin" in plugin_names
        assert "disabled-plugin" not in plugin_names


class TestPluginSettingsValidation:
    """Test plugin settings validation."""

    def test_valid_plugin_settings(self):
        """Test creating config with valid plugin settings."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            plugins=PluginConfig(
                enabled=True,
                plugin_dir="plugins",
                plugin_settings=[
                    {
                        "plugin_name": "test-plugin",
                        "enabled": True,
                        "priority": 10,
                        "settings": {"key": "value"},
                    }
                ],
            ),
        )

        assert config.plugins.plugin_settings[0].plugin_name == "test-plugin"

    def test_plugin_settings_with_empty_settings(self):
        """Test plugin settings with empty settings dict."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            plugins=PluginConfig(
                enabled=True,
                plugin_dir="plugins",
                plugin_settings=[
                    {
                        "plugin_name": "test-plugin",
                        "enabled": True,
                        "priority": 100,
                        "settings": {},
                    }
                ],
            ),
        )

        settings = config.plugins.get_plugin_settings("test-plugin")
        assert settings == {}

    def test_plugin_settings_defaults(self):
        """Test plugin settings default values."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            plugins=PluginConfig(
                enabled=True,
                plugin_dir="plugins",
                plugin_settings=[
                    {
                        "plugin_name": "test-plugin",
                        # enabled defaults to True
                        # priority defaults to 100
                        "settings": {"key": "value"},
                    }
                ],
            ),
        )

        plugin_setting = config.plugins.plugin_settings[0]
        assert plugin_setting.enabled is True
        assert plugin_setting.priority == 100


class TestPluginConfigIntegration:
    """Test plugin configuration integration."""

    def test_plugin_uses_config_in_lifecycle(self, mock_plugin):
        """Test that plugin can access config during lifecycle."""
        # Simulate on_load
        mock_plugin.on_load()

        # Plugin should be able to access config
        api_key = mock_plugin.get_config_value("api_key")
        assert api_key == "test-key-123"

    def test_plugin_config_persists(self, mock_plugin):
        """Test that plugin config persists across calls."""
        value1 = mock_plugin.get_config_value("threshold")
        value2 = mock_plugin.get_config_value("threshold")

        assert value1 == value2
        assert value1 == 80

    def test_multiple_plugins_independent_config(self, mock_config):
        """Test that multiple plugins have independent configs."""
        from feishu_webhook_bot.core.client import FeishuWebhookClient
        from feishu_webhook_bot.core.config import WebhookConfig

        webhook_config = WebhookConfig(url="https://example.com/webhook", name="test")
        client = FeishuWebhookClient(config=webhook_config)
        plugin1 = MockPlugin(config=mock_config, client=client)
        plugin2 = MockPlugin(config=mock_config, client=client)

        # Both should access the same config
        config1 = plugin1.get_all_config()
        config2 = plugin2.get_all_config()

        assert config1 == config2
