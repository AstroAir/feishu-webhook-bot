"""Tests for plugins.config_updater module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
from pydantic import Field

from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema
from feishu_webhook_bot.plugins.config_updater import ConfigUpdater


class MockConfigSchema(PluginConfigSchema):
    """Mock config schema for testing."""

    api_key: str = Field(
        ...,
        description="API key for authentication",
        json_schema_extra={"example": "sk-xxx", "env_var": "API_KEY"},
    )
    timeout: int = Field(default=30, description="Timeout in seconds")


class TestConfigUpdater:
    """Tests for ConfigUpdater."""

    def test_init(self) -> None:
        """Test ConfigUpdater initialization."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            assert updater.config_path == config_path
        finally:
            config_path.unlink(missing_ok=True)

    def test_backup_creates_backup_file(self) -> None:
        """Test backup creates a backup file."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("test: value\n")
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            backup_path = updater.backup()

            assert backup_path.exists()
            assert ".backup.yaml" in backup_path.name
            assert backup_path.read_text() == "test: value\n"

            backup_path.unlink()
        finally:
            config_path.unlink(missing_ok=True)

    def test_update_plugin_settings_new_plugin(self) -> None:
        """Test updating settings for a new plugin."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("plugins:\n  plugin_settings: []\n")
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            updater.update_plugin_settings(
                "test-plugin",
                {"api_key": "secret123", "timeout": 60},
                create_backup=False,
            )

            config = yaml.safe_load(config_path.read_text())
            plugin_settings = config["plugins"]["plugin_settings"]

            assert len(plugin_settings) == 1
            assert plugin_settings[0]["plugin_name"] == "test-plugin"
            assert plugin_settings[0]["settings"]["api_key"] == "secret123"
            assert plugin_settings[0]["settings"]["timeout"] == 60
        finally:
            config_path.unlink(missing_ok=True)

    def test_update_plugin_settings_existing_plugin(self) -> None:
        """Test updating settings for an existing plugin."""
        initial_config = {
            "plugins": {
                "plugin_settings": [
                    {
                        "plugin_name": "test-plugin",
                        "enabled": True,
                        "settings": {"api_key": "old_key"},
                    }
                ]
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(initial_config, f)
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            updater.update_plugin_settings(
                "test-plugin",
                {"api_key": "new_key", "timeout": 60},
                create_backup=False,
            )

            config = yaml.safe_load(config_path.read_text())
            plugin_settings = config["plugins"]["plugin_settings"]

            assert len(plugin_settings) == 1
            assert plugin_settings[0]["settings"]["api_key"] == "new_key"
            assert plugin_settings[0]["settings"]["timeout"] == 60
        finally:
            config_path.unlink(missing_ok=True)

    def test_update_plugin_settings_creates_plugins_section(self) -> None:
        """Test updating settings creates plugins section if missing."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("other: value\n")
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            updater.update_plugin_settings(
                "test-plugin",
                {"api_key": "secret"},
                create_backup=False,
            )

            config = yaml.safe_load(config_path.read_text())

            assert "plugins" in config
            assert "plugin_settings" in config["plugins"]
            assert len(config["plugins"]["plugin_settings"]) == 1
        finally:
            config_path.unlink(missing_ok=True)

    def test_remove_plugin_settings(self) -> None:
        """Test removing plugin settings."""
        initial_config = {
            "plugins": {
                "plugin_settings": [
                    {"plugin_name": "plugin-a", "settings": {}},
                    {"plugin_name": "plugin-b", "settings": {}},
                ]
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(initial_config, f)
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            result = updater.remove_plugin_settings("plugin-a")

            assert result is True

            config = yaml.safe_load(config_path.read_text())
            plugin_names = [p["plugin_name"] for p in config["plugins"]["plugin_settings"]]

            assert "plugin-a" not in plugin_names
            assert "plugin-b" in plugin_names

            for backup in config_path.parent.glob("*.backup.yaml"):
                backup.unlink()
        finally:
            config_path.unlink(missing_ok=True)

    def test_remove_plugin_settings_not_found(self) -> None:
        """Test removing non-existent plugin settings returns False."""
        initial_config = {
            "plugins": {
                "plugin_settings": [
                    {"plugin_name": "plugin-a", "settings": {}},
                ]
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(initial_config, f)
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            result = updater.remove_plugin_settings("nonexistent")

            assert result is False
        finally:
            config_path.unlink(missing_ok=True)

    def test_get_plugin_settings(self) -> None:
        """Test getting plugin settings."""
        initial_config = {
            "plugins": {
                "plugin_settings": [
                    {
                        "plugin_name": "test-plugin",
                        "settings": {"api_key": "secret", "timeout": 60},
                    },
                ]
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(initial_config, f)
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            settings = updater.get_plugin_settings("test-plugin")

            assert settings == {"api_key": "secret", "timeout": 60}
        finally:
            config_path.unlink(missing_ok=True)

    def test_get_plugin_settings_not_found(self) -> None:
        """Test getting settings for non-existent plugin."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("plugins:\n  plugin_settings: []\n")
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            settings = updater.get_plugin_settings("nonexistent")

            assert settings == {}
        finally:
            config_path.unlink(missing_ok=True)

    def test_list_configured_plugins(self) -> None:
        """Test listing configured plugins."""
        initial_config = {
            "plugins": {
                "plugin_settings": [
                    {"plugin_name": "plugin-a", "settings": {}},
                    {"plugin_name": "plugin-b", "settings": {}},
                ]
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(initial_config, f)
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            plugins = updater.list_configured_plugins()

            assert "plugin-a" in plugins
            assert "plugin-b" in plugins
            assert len(plugins) == 2
        finally:
            config_path.unlink(missing_ok=True)

    def test_list_configured_plugins_empty(self) -> None:
        """Test listing plugins when none configured."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("")
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            plugins = updater.list_configured_plugins()

            assert plugins == []
        finally:
            config_path.unlink(missing_ok=True)

    def test_load_config_nonexistent_file(self) -> None:
        """Test loading config from non-existent file returns empty dict."""
        config_path = Path("/nonexistent/path/config.yaml")
        updater = ConfigUpdater(config_path)

        config = updater._load_config()

        assert config == {}

    def test_generate_template_string(self) -> None:
        """Test generating template string."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("")
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            template_str = updater.generate_template_string("test-plugin", MockConfigSchema)

            assert "test-plugin" in template_str
            assert "plugins" in template_str
            assert "plugin_settings" in template_str
        finally:
            config_path.unlink(missing_ok=True)

    def test_add_plugin_template(self) -> None:
        """Test adding plugin template."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("plugins:\n  plugin_settings: []\n")
            config_path = Path(f.name)

        try:
            updater = ConfigUpdater(config_path)
            updater.add_plugin_template("test-plugin", MockConfigSchema, include_comments=False)

            config = yaml.safe_load(config_path.read_text())
            plugin_settings = config["plugins"]["plugin_settings"]

            assert len(plugin_settings) >= 1

            for backup in config_path.parent.glob("*.backup.yaml"):
                backup.unlink()
        finally:
            config_path.unlink(missing_ok=True)
