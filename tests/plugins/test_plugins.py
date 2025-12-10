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
