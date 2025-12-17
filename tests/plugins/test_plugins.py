"""Tests for the plugin system."""

import time
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.core import BotConfig
from feishu_webhook_bot.core.config import PluginConfig
from feishu_webhook_bot.plugins import BasePlugin, PluginManager


@pytest.fixture
def mock_client():
    """Provides a mock FeishuWebhookClient."""
    return MagicMock()


@pytest.fixture
def mock_scheduler():
    """Provides a mock TaskScheduler."""
    return MagicMock()


@pytest.fixture
def plugin_dir(tmp_path):
    """Creates a temporary plugin directory."""
    return tmp_path


@pytest.fixture
def create_plugin_file(plugin_dir):
    """A factory to create plugin files for testing."""

    def _create_plugin_file(name: str, content: str):
        file_path = plugin_dir / f"{name}.py"
        file_path.write_text(content)
        return file_path

    return _create_plugin_file


SIMPLE_PLUGIN_CONTENT = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class MyTestPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="test-plugin")
    def on_load(self): pass
    def on_enable(self): pass
    def on_disable(self): pass
    def on_unload(self): pass
"""


def test_plugin_manager_discover_and_load(plugin_dir, create_plugin_file, mock_client):
    """Test plugin discovery and loading."""
    create_plugin_file("plugin1", SIMPLE_PLUGIN_CONTENT)
    config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))

    manager = PluginManager(config, mock_client)
    manager.load_plugins()

    assert len(manager.plugins) == 1
    assert "test-plugin" in manager.plugins
    assert isinstance(manager.get_plugin("test-plugin"), BasePlugin)


def test_plugin_manager_handles_load_error(plugin_dir, create_plugin_file, mock_client):
    """Test that the manager gracefully handles plugins that fail to load."""
    create_plugin_file("bad_plugin", "import non_existent_module")
    create_plugin_file("good_plugin", SIMPLE_PLUGIN_CONTENT)
    config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))

    manager = PluginManager(config, mock_client)
    manager.load_plugins()

    # Should load the good plugin and skip the bad one without crashing
    assert len(manager.plugins) == 1
    assert "test-plugin" in manager.plugins


def test_enable_all_and_disable_all(plugin_dir, create_plugin_file, mock_client):
    """Test the enable_all and disable_all methods."""
    create_plugin_file("plugin1", SIMPLE_PLUGIN_CONTENT)
    config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
    manager = PluginManager(config, mock_client)
    manager.load_plugins()

    plugin = manager.get_plugin("test-plugin")
    assert plugin is not None
    plugin.on_enable = MagicMock()
    plugin.on_disable = MagicMock()

    manager.enable_all()
    plugin.on_enable.assert_called_once()

    manager.disable_all()
    plugin.on_disable.assert_called_once()


def test_plugin_schedules_jobs(plugin_dir, create_plugin_file, mock_client, mock_scheduler):
    """Test that plugins can register and clean up scheduled jobs."""
    job_plugin_content = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from feishu_webhook_bot.scheduler import job

class JobPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="job-plugin")

    @job(trigger='interval', minutes=5)
    def my_scheduled_task(self):
        pass

    def on_enable(self):
        self.job_id = self.register_job(self.my_scheduled_task)
"""
    create_plugin_file("job_plugin", job_plugin_content)
    config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
    manager = PluginManager(config, mock_client, mock_scheduler)
    manager.load_plugins()
    manager.enable_all()

    # Verify job was added
    mock_scheduler.add_job.assert_called_once()
    plugin = manager.get_plugin("job-plugin")
    assert plugin is not None
    assert len(plugin._job_ids) == 1
    job_id = plugin._job_ids[0]

    # Verify job is removed on disable
    manager.disable_plugin("job-plugin")
    mock_scheduler.remove_job.assert_called_once_with(job_id)


@patch("feishu_webhook_bot.plugins.manager.Observer")
def test_hot_reload_lifecycle(mock_observer_class, plugin_dir, mock_client):
    """Test that hot-reloading starts and stops the observer."""
    config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir), auto_reload=True))
    manager = PluginManager(config, mock_client)

    mock_observer_instance = MagicMock()
    mock_observer_class.return_value = mock_observer_instance

    manager.start_hot_reload()
    mock_observer_instance.schedule.assert_called_once()
    mock_observer_instance.start.assert_called_once()

    manager.stop_hot_reload()
    mock_observer_instance.stop.assert_called_once()
    mock_observer_instance.join.assert_called_once()


@pytest.mark.slow  # This test involves file I/O and timing
def test_hot_reload_triggers_on_file_events(plugin_dir, create_plugin_file, mock_client):
    """Test that file events (create, modify, delete) trigger a reload."""
    config = BotConfig(
        plugins=PluginConfig(
            plugin_dir=str(plugin_dir),
            auto_reload=True,
            reload_delay=0.1,
        )
    )
    manager = PluginManager(config, mock_client)
    manager.reload_plugins = MagicMock()

    manager.start_hot_reload()
    time.sleep(0.2)  # Give observer time to start

    # Test file creation
    create_plugin_file("new_plugin", SIMPLE_PLUGIN_CONTENT)
    time.sleep(0.2)  # Wait for event propagation
    manager.reload_plugins.assert_called_once()
    manager.reload_plugins.reset_mock()

    # Test file modification
    plugin_to_modify = create_plugin_file("another_plugin", SIMPLE_PLUGIN_CONTENT)
    time.sleep(0.2)
    manager.reload_plugins.assert_called_once()  # Initial creation
    manager.reload_plugins.reset_mock()

    plugin_to_modify.write_text(SIMPLE_PLUGIN_CONTENT + "\n# a comment")
    time.sleep(0.2)
    manager.reload_plugins.assert_called_once()
    manager.reload_plugins.reset_mock()

    # Test file deletion
    plugin_to_modify.unlink()
    time.sleep(0.2)
    manager.reload_plugins.assert_called_once()

    manager.stop_hot_reload()


# =============================================================================
# Enhanced PluginManager Tests
# =============================================================================


PLUGIN_WITH_SCHEMA_CONTENT = """
from pydantic import Field
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema

class SchemaPluginConfig(PluginConfigSchema):
    api_key: str = Field(..., description="API key")
    timeout: int = Field(default=30, description="Timeout")

class SchemaPlugin(BasePlugin):
    config_schema = SchemaPluginConfig

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="schema-plugin", version="1.0.0")
"""


PLUGIN_WITH_PERMISSIONS_CONTENT = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from feishu_webhook_bot.plugins.permissions import PluginPermission

class PermissionPlugin(BasePlugin):
    PERMISSIONS = [PluginPermission.NETWORK_SEND, PluginPermission.FILE_READ]

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="permission-plugin", version="1.0.0")
"""


class TestPluginManagerEnhanced:
    """Tests for enhanced PluginManager functionality."""

    @pytest.fixture
    def manager_with_plugin(self, plugin_dir, create_plugin_file, mock_client):
        """Create a manager with a loaded plugin."""
        create_plugin_file("test_plugin", SIMPLE_PLUGIN_CONTENT)
        config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
        manager = PluginManager(config, mock_client)
        manager.load_plugins()
        return manager

    def test_reload_plugin(self, plugin_dir, create_plugin_file, mock_client):
        """Test reloading a specific plugin."""
        plugin_file = create_plugin_file("reload_plugin", SIMPLE_PLUGIN_CONTENT)
        config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
        manager = PluginManager(config, mock_client)
        manager.load_plugins()
        manager.enable_all()

        # Modify plugin file
        new_content = SIMPLE_PLUGIN_CONTENT.replace(
            'name="test-plugin"', 'name="test-plugin", version="2.0.0"'
        )
        plugin_file.write_text(new_content)

        # Reload specific plugin
        result = manager.reload_plugin("test-plugin")
        assert result is True

    def test_reload_plugin_not_found(self, manager_with_plugin):
        """Test reloading a non-existent plugin."""
        result = manager_with_plugin.reload_plugin("nonexistent")
        assert result is False

    def test_get_plugin_info(self, manager_with_plugin):
        """Test getting detailed plugin info."""
        info = manager_with_plugin.get_plugin_info("test-plugin")

        assert info is not None
        assert info.name == "test-plugin"
        assert info.version == "1.0.0"
        assert info.file_path != ""
        assert info.load_time > 0

    def test_get_plugin_info_not_found(self, manager_with_plugin):
        """Test getting info for non-existent plugin."""
        info = manager_with_plugin.get_plugin_info("nonexistent")
        assert info is None

    def test_get_all_plugin_info(self, plugin_dir, create_plugin_file, mock_client):
        """Test getting info for all plugins."""
        create_plugin_file("plugin1", SIMPLE_PLUGIN_CONTENT)
        create_plugin_file("plugin2", SIMPLE_PLUGIN_CONTENT.replace("test-plugin", "test-plugin-2"))
        config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
        manager = PluginManager(config, mock_client)
        manager.load_plugins()

        all_info = manager.get_all_plugin_info()
        assert len(all_info) >= 1

    def test_is_plugin_enabled(self, manager_with_plugin):
        """Test checking if plugin is enabled."""
        assert manager_with_plugin.is_plugin_enabled("test-plugin") is False

        manager_with_plugin.enable_plugin("test-plugin")
        assert manager_with_plugin.is_plugin_enabled("test-plugin") is True

        manager_with_plugin.disable_plugin("test-plugin")
        assert manager_with_plugin.is_plugin_enabled("test-plugin") is False

    def test_list_plugins(self, manager_with_plugin):
        """Test listing loaded plugins."""
        plugins = manager_with_plugin.list_plugins()
        assert "test-plugin" in plugins

    def test_get_plugin_config(self, plugin_dir, create_plugin_file, mock_client):
        """Test getting plugin configuration."""
        from feishu_webhook_bot.core.config import PluginSettingsConfig

        create_plugin_file("config_plugin", SIMPLE_PLUGIN_CONTENT)
        config = BotConfig(
            plugins=PluginConfig(
                plugin_dir=str(plugin_dir),
                plugin_settings=[
                    PluginSettingsConfig(
                        plugin_name="test-plugin",
                        settings={"api_key": "secret", "timeout": 60},
                    )
                ],
            )
        )
        manager = PluginManager(config, mock_client)
        manager.load_plugins()

        plugin_config = manager.get_plugin_config("test-plugin")
        assert plugin_config["api_key"] == "secret"
        assert plugin_config["timeout"] == 60

    def test_get_available_plugins(self, manager_with_plugin):
        """Test getting available plugins list."""
        available = manager_with_plugin.get_available_plugins()
        assert len(available) >= 1
        assert any(p["name"] == "test-plugin" for p in available)

    def test_dispatch_event(self, plugin_dir, create_plugin_file, mock_client):
        """Test dispatching events to plugins."""
        event_plugin_content = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class EventPlugin(BasePlugin):
    received_events = []

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="event-plugin")

    def handle_event(self, event, context=None):
        EventPlugin.received_events.append(event)
"""
        create_plugin_file("event_plugin", event_plugin_content)
        config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
        manager = PluginManager(config, mock_client)
        manager.load_plugins()

        test_event = {"type": "message", "content": "test"}
        manager.dispatch_event(test_event)

        plugin = manager.get_plugin("event-plugin")
        assert len(plugin.__class__.received_events) == 1
        assert plugin.__class__.received_events[0]["type"] == "message"


class TestPluginManagerPermissions:
    """Tests for PluginManager permission management."""

    @pytest.fixture
    def manager_with_perm_plugin(self, plugin_dir, create_plugin_file, mock_client):
        """Create manager with permission plugin."""
        create_plugin_file("perm_plugin", PLUGIN_WITH_PERMISSIONS_CONTENT)
        config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
        manager = PluginManager(config, mock_client)
        manager.load_plugins()
        return manager

    def test_get_permission_manager(self, manager_with_perm_plugin):
        """Test getting permission manager."""
        pm = manager_with_perm_plugin.get_permission_manager()
        assert pm is not None

    def test_register_plugin_permissions(self, manager_with_perm_plugin):
        """Test that plugin permissions are registered on load."""
        pm = manager_with_perm_plugin.get_permission_manager()
        perms = pm.get_plugin_permissions("permission-plugin")
        assert perms is not None

    def test_get_plugin_permissions(self, manager_with_perm_plugin):
        """Test getting plugin permission status."""
        perms = manager_with_perm_plugin.get_plugin_permissions("permission-plugin")
        assert "required" in perms
        assert "granted" in perms
        assert "NETWORK_SEND" in perms["required"]

    def test_grant_plugin_permission(self, manager_with_perm_plugin):
        """Test granting a permission to plugin."""
        result = manager_with_perm_plugin.grant_plugin_permission(
            "permission-plugin", "SYSTEM_EXEC"
        )
        assert result is True

        perms = manager_with_perm_plugin.get_plugin_permissions("permission-plugin")
        assert "SYSTEM_EXEC" in perms["granted"]

    def test_revoke_plugin_permission(self, manager_with_perm_plugin):
        """Test revoking a permission from plugin."""
        manager_with_perm_plugin.grant_plugin_permission("permission-plugin", "SYSTEM_EXEC")
        result = manager_with_perm_plugin.revoke_plugin_permission(
            "permission-plugin", "SYSTEM_EXEC"
        )
        assert result is True


class TestPluginManagerSandbox:
    """Tests for PluginManager sandbox functionality."""

    @pytest.fixture
    def manager(self, plugin_dir, create_plugin_file, mock_client):
        """Create manager with plugin."""
        create_plugin_file("sandbox_plugin", SIMPLE_PLUGIN_CONTENT)
        config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
        manager = PluginManager(config, mock_client)
        manager.load_plugins()
        return manager

    def test_get_sandbox(self, manager):
        """Test getting sandbox instance."""
        sandbox = manager.get_sandbox()
        assert sandbox is not None

    def test_get_sandbox_violations_empty(self, manager):
        """Test getting violations when none exist."""
        violations = manager.get_sandbox_violations("test-plugin")
        assert violations == []


class TestPluginManagerMultiProvider:
    """Tests for PluginManager multi-provider support."""

    def test_manager_with_providers(self, plugin_dir, create_plugin_file):
        """Test manager initialization with multiple providers."""
        create_plugin_file("provider_plugin", SIMPLE_PLUGIN_CONTENT)

        mock_providers = {
            "feishu": MagicMock(),
            "qq": MagicMock(),
            "telegram": MagicMock(),
        }

        config = BotConfig(plugins=PluginConfig(plugin_dir=str(plugin_dir)))
        manager = PluginManager(config, None, None, providers=mock_providers)
        manager.load_plugins()

        plugin = manager.get_plugin("test-plugin")
        assert plugin is not None
        assert plugin.providers == mock_providers
        assert plugin.get_provider("feishu") is not None
        assert plugin.get_provider("qq") is not None


class TestPluginInfo:
    """Tests for PluginInfo dataclass."""

    def test_plugin_info_to_dict(self):
        """Test PluginInfo to_dict method."""
        from feishu_webhook_bot.plugins.manager import PluginInfo

        info = PluginInfo(
            name="test-plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            enabled=True,
            file_path="/path/to/plugin.py",
            config={"key": "value"},
            has_schema=True,
            jobs=["job1", "job2"],
            load_time=1234567890.0,
            permissions=["NETWORK_SEND"],
            permissions_granted=True,
        )

        data = info.to_dict()
        assert data["name"] == "test-plugin"
        assert data["version"] == "1.0.0"
        assert data["enabled"] is True
        assert data["has_schema"] is True
        assert "job1" in data["jobs"]
        assert "NETWORK_SEND" in data["permissions"]
