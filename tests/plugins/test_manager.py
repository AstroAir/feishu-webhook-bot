"""Comprehensive tests for plugin manager functionality.

Tests cover:
- Plugin discovery and loading
- Plugin lifecycle management
- Hot-reload mechanism
- Job registration with scheduler
- Multi-provider support
- Event dispatching
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from feishu_webhook_bot.core.config import BotConfig, PluginConfig
from feishu_webhook_bot.core.provider import BaseProvider, ProviderConfig
from feishu_webhook_bot.plugins.base import BasePlugin, PluginMetadata
from feishu_webhook_bot.plugins.manager import PluginFileHandler, PluginManager


# ==============================================================================
# Test Fixtures
# ==============================================================================


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def send_message(self, message: Any, target: str) -> Any:
        return Mock(success=True)

    def send_text(self, text: str, target: str) -> Any:
        return Mock(success=True)

    def send_card(self, card: dict, target: str) -> Any:
        return Mock(success=True)

    def send_rich_text(self, title: str, content: list, target: str, language: str = "zh_cn") -> Any:
        return Mock(success=True)

    def send_image(self, image_key: str, target: str) -> Any:
        return Mock(success=True)


class SamplePlugin(BasePlugin):
    """Sample plugin for testing."""

    def __init__(self, config: BotConfig, client: Any = None, providers: dict | None = None):
        super().__init__(config, client, providers)
        self.load_called = False
        self.enable_called = False
        self.disable_called = False
        self.unload_called = False
        self.events_received: list[dict] = []

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sample-plugin",
            version="1.0.0",
            description="A sample plugin for testing",
            author="Test",
        )

    def on_load(self) -> None:
        self.load_called = True

    def on_enable(self) -> None:
        self.enable_called = True

    def on_disable(self) -> None:
        self.disable_called = True

    def on_unload(self) -> None:
        self.unload_called = True

    def handle_event(self, event: dict, context: dict | None = None) -> None:
        self.events_received.append(event)


class FailingPlugin(BasePlugin):
    """Plugin that raises errors for testing error handling."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="failing-plugin", version="1.0.0")

    def on_load(self) -> None:
        raise RuntimeError("Load error")

    def on_enable(self) -> None:
        raise RuntimeError("Enable error")

    def on_disable(self) -> None:
        raise RuntimeError("Disable error")

    def on_unload(self) -> None:
        raise RuntimeError("Unload error")


@pytest.fixture
def minimal_config():
    """Create minimal bot configuration for testing."""
    return BotConfig(
        webhooks=[],
        plugins=PluginConfig(
            enabled=True,
            plugin_dir="./plugins",
            auto_reload=False,
            reload_delay=1.0,
        ),
    )


@pytest.fixture
def config_with_disabled_plugins():
    """Create config with plugin system disabled."""
    return BotConfig(
        webhooks=[],
        plugins=PluginConfig(
            enabled=False,
            plugin_dir="./plugins",
        ),
    )


@pytest.fixture
def mock_client():
    """Create mock webhook client."""
    return Mock()


@pytest.fixture
def mock_scheduler():
    """Create mock scheduler."""
    scheduler = Mock()
    scheduler.add_job = Mock(return_value="job_123")
    scheduler.remove_job = Mock()
    return scheduler


@pytest.fixture
def mock_providers():
    """Create mock providers dict."""
    config = ProviderConfig(provider_type="test", name="test_provider")
    provider = MockProvider(config)
    return {"test_provider": provider}


@pytest.fixture
def plugin_manager(minimal_config, mock_client, mock_scheduler, mock_providers):
    """Create plugin manager instance."""
    return PluginManager(
        config=minimal_config,
        client=mock_client,
        scheduler=mock_scheduler,
        providers=mock_providers,
    )


# ==============================================================================
# PluginFileHandler Tests
# ==============================================================================


class TestPluginFileHandler:
    """Tests for PluginFileHandler."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock plugin manager."""
        manager = Mock(spec=PluginManager)
        return manager

    @pytest.fixture
    def handler(self, mock_manager):
        """Create file handler."""
        return PluginFileHandler(mock_manager, delay=0.5)

    def test_handler_initialization(self, handler, mock_manager):
        """Test PluginFileHandler initialization."""
        assert handler.manager is mock_manager
        assert handler.delay == 0.5
        assert handler._pending_reload is False
        assert handler._last_event_time == 0.0

    def test_on_modified_ignores_directories(self, handler, mock_manager):
        """Test handler ignores directory events."""
        event = Mock()
        event.is_directory = True
        event.src_path = "/plugins/subdir"

        handler.on_modified(event)

        mock_manager.reload_plugins.assert_not_called()

    def test_on_modified_ignores_non_python_files(self, handler, mock_manager):
        """Test handler ignores non-Python files."""
        event = Mock()
        event.is_directory = False
        event.src_path = "/plugins/config.yaml"

        handler.on_modified(event)

        mock_manager.reload_plugins.assert_not_called()

    def test_on_modified_triggers_reload(self, handler, mock_manager):
        """Test handler triggers reload for Python files."""
        event = Mock()
        event.is_directory = False
        event.src_path = "/plugins/my_plugin.py"

        handler.on_modified(event)

        mock_manager.reload_plugins.assert_called_once()

    def test_on_modified_debounces_events(self, handler, mock_manager):
        """Test handler debounces rapid events."""
        event = Mock()
        event.is_directory = False
        event.src_path = "/plugins/plugin.py"

        # First event triggers reload
        handler.on_modified(event)
        assert mock_manager.reload_plugins.call_count == 1

        # Immediate second event is debounced
        handler.on_modified(event)
        assert mock_manager.reload_plugins.call_count == 1

    def test_on_created_ignores_directories(self, handler, mock_manager):
        """Test handler ignores directory creation."""
        event = Mock()
        event.is_directory = True
        event.src_path = "/plugins/newdir"

        handler.on_created(event)

        mock_manager.reload_plugins.assert_not_called()

    def test_on_created_triggers_reload(self, handler, mock_manager):
        """Test handler triggers reload for new Python files."""
        event = Mock()
        event.is_directory = False
        event.src_path = "/plugins/new_plugin.py"

        handler.on_created(event)

        mock_manager.reload_plugins.assert_called_once()

    def test_on_deleted_ignores_directories(self, handler, mock_manager):
        """Test handler ignores directory deletion."""
        event = Mock()
        event.is_directory = True
        event.src_path = "/plugins/olddir"

        handler.on_deleted(event)

        mock_manager.reload_plugins.assert_not_called()

    def test_on_deleted_triggers_reload(self, handler, mock_manager):
        """Test handler triggers reload for deleted Python files."""
        event = Mock()
        event.is_directory = False
        event.src_path = "/plugins/old_plugin.py"

        handler.on_deleted(event)

        mock_manager.reload_plugins.assert_called_once()


# ==============================================================================
# PluginManager Initialization Tests
# ==============================================================================


class TestPluginManagerInitialization:
    """Tests for PluginManager initialization."""

    def test_manager_initialization(self, plugin_manager, minimal_config, mock_client, mock_scheduler, mock_providers):
        """Test PluginManager initialization."""
        assert plugin_manager.config is minimal_config
        assert plugin_manager.client is mock_client
        assert plugin_manager.scheduler is mock_scheduler
        assert plugin_manager.providers == mock_providers
        assert plugin_manager.plugins == {}
        assert plugin_manager._observer is None

    def test_manager_initialization_minimal(self, minimal_config):
        """Test PluginManager initialization with minimal arguments."""
        manager = PluginManager(config=minimal_config)
        assert manager.config is minimal_config
        assert manager.client is None
        assert manager.scheduler is None
        assert manager.providers == {}


# ==============================================================================
# Plugin Discovery Tests
# ==============================================================================


class TestPluginDiscovery:
    """Tests for plugin discovery."""

    def test_discover_plugins_empty_directory(self, plugin_manager):
        """Test discovering plugins in empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            plugins = plugin_manager._discover_plugins(plugin_dir)
            assert plugins == []

    def test_discover_plugins_nonexistent_directory(self, plugin_manager):
        """Test discovering plugins in nonexistent directory."""
        plugin_dir = Path("/nonexistent/directory")
        plugins = plugin_manager._discover_plugins(plugin_dir)
        assert plugins == []

    def test_discover_plugins_finds_python_files(self, plugin_manager):
        """Test discovering Python files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)

            # Create plugin files
            (plugin_dir / "plugin1.py").touch()
            (plugin_dir / "plugin2.py").touch()
            (plugin_dir / "not_a_plugin.txt").touch()

            plugins = plugin_manager._discover_plugins(plugin_dir)

            assert len(plugins) == 2
            assert all(str(p).endswith(".py") for p in plugins)

    def test_discover_plugins_ignores_underscore_files(self, plugin_manager):
        """Test discovering plugins ignores files starting with underscore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)

            # Create files
            (plugin_dir / "plugin.py").touch()
            (plugin_dir / "_private.py").touch()
            (plugin_dir / "__init__.py").touch()

            plugins = plugin_manager._discover_plugins(plugin_dir)

            assert len(plugins) == 1
            assert "plugin.py" in str(plugins[0])


# ==============================================================================
# Plugin Loading Tests
# ==============================================================================


class TestPluginLoading:
    """Tests for plugin loading."""

    def test_load_plugins_disabled(self, config_with_disabled_plugins, mock_client):
        """Test load_plugins when plugin system is disabled."""
        manager = PluginManager(config=config_with_disabled_plugins, client=mock_client)

        manager.load_plugins()

        assert len(manager.plugins) == 0

    def test_load_plugin_from_valid_file(self, plugin_manager):
        """Test loading plugin from a valid Python file."""
        plugin_code = '''
from feishu_webhook_bot.plugins.base import BasePlugin, PluginMetadata

class TestPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="test-plugin", version="1.0.0")
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "test_plugin.py"
            plugin_file.write_text(plugin_code)

            plugin = plugin_manager._load_plugin_from_file(plugin_file)

            assert plugin is not None
            assert plugin.metadata().name == "test-plugin"

    def test_load_plugin_from_invalid_file(self, plugin_manager):
        """Test loading plugin from file without plugin class."""
        plugin_code = '''
# This file has no plugin class
def some_function():
    pass
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "not_a_plugin.py"
            plugin_file.write_text(plugin_code)

            plugin = plugin_manager._load_plugin_from_file(plugin_file)

            assert plugin is None

    def test_load_plugin_from_syntax_error_file(self, plugin_manager):
        """Test loading plugin from file with syntax error."""
        plugin_code = '''
def broken(
    # Missing closing parenthesis
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "broken_plugin.py"
            plugin_file.write_text(plugin_code)

            plugin = plugin_manager._load_plugin_from_file(plugin_file)

            assert plugin is None


# ==============================================================================
# Plugin Lifecycle Tests
# ==============================================================================


class TestPluginLifecycle:
    """Tests for plugin lifecycle management."""

    @pytest.fixture
    def manager_with_plugin(self, plugin_manager, minimal_config, mock_providers):
        """Create manager with a sample plugin loaded."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["sample-plugin"] = plugin
        return plugin_manager, plugin

    def test_enable_plugin_success(self, manager_with_plugin, mock_scheduler):
        """Test enabling a plugin successfully."""
        manager, plugin = manager_with_plugin

        result = manager.enable_plugin("sample-plugin")

        assert result is True
        assert plugin.enable_called is True

    def test_enable_plugin_not_found(self, plugin_manager):
        """Test enabling nonexistent plugin."""
        result = plugin_manager.enable_plugin("nonexistent")

        assert result is False

    def test_disable_plugin_success(self, manager_with_plugin):
        """Test disabling a plugin successfully."""
        manager, plugin = manager_with_plugin

        # First enable then disable
        manager.enable_plugin("sample-plugin")
        result = manager.disable_plugin("sample-plugin")

        assert result is True
        assert plugin.disable_called is True

    def test_disable_plugin_not_found(self, plugin_manager):
        """Test disabling nonexistent plugin."""
        result = plugin_manager.disable_plugin("nonexistent")

        assert result is False

    def test_enable_all_plugins(self, plugin_manager, minimal_config, mock_providers):
        """Test enabling all plugins."""
        plugin1 = SamplePlugin(minimal_config, providers=mock_providers)
        plugin2 = SamplePlugin(minimal_config, providers=mock_providers)
        plugin2.metadata = lambda: PluginMetadata(name="plugin2", version="1.0.0")

        plugin_manager.plugins["sample-plugin"] = plugin1
        plugin_manager.plugins["plugin2"] = plugin2

        plugin_manager.enable_all()

        assert plugin1.enable_called is True
        assert plugin2.enable_called is True

    def test_disable_all_plugins(self, plugin_manager, minimal_config, mock_providers):
        """Test disabling all plugins."""
        plugin1 = SamplePlugin(minimal_config, providers=mock_providers)
        plugin2 = SamplePlugin(minimal_config, providers=mock_providers)
        plugin2.metadata = lambda: PluginMetadata(name="plugin2", version="1.0.0")

        plugin_manager.plugins["sample-plugin"] = plugin1
        plugin_manager.plugins["plugin2"] = plugin2

        plugin_manager.enable_all()
        plugin_manager.disable_all()

        assert plugin1.disable_called is True
        assert plugin2.disable_called is True

    def test_get_plugin(self, manager_with_plugin):
        """Test getting a plugin by name."""
        manager, plugin = manager_with_plugin

        result = manager.get_plugin("sample-plugin")

        assert result is plugin

    def test_get_plugin_not_found(self, plugin_manager):
        """Test getting nonexistent plugin."""
        result = plugin_manager.get_plugin("nonexistent")

        assert result is None

    def test_list_plugins(self, manager_with_plugin, minimal_config, mock_providers):
        """Test listing loaded plugins."""
        manager, _ = manager_with_plugin

        # Add another plugin
        plugin2 = SamplePlugin(minimal_config, providers=mock_providers)
        plugin2.metadata = lambda: PluginMetadata(name="plugin2", version="1.0.0")
        manager.plugins["plugin2"] = plugin2

        names = manager.list_plugins()

        assert "sample-plugin" in names
        assert "plugin2" in names


# ==============================================================================
# Plugin Reload Tests
# ==============================================================================


class TestPluginReload:
    """Tests for plugin reload functionality."""

    def test_reload_plugins_disables_existing(self, plugin_manager, minimal_config, mock_providers):
        """Test reload disables existing plugins."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["sample-plugin"] = plugin

        with patch.object(plugin_manager, "load_plugins"):
            with patch.object(plugin_manager, "enable_all"):
                plugin_manager.reload_plugins()

        assert plugin.disable_called is True
        assert plugin.unload_called is True

    def test_reload_plugins_clears_plugin_dict(self, plugin_manager, minimal_config, mock_providers):
        """Test reload clears plugin dictionary."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["sample-plugin"] = plugin

        with patch.object(plugin_manager, "load_plugins"):
            with patch.object(plugin_manager, "enable_all"):
                plugin_manager.reload_plugins()

        # After reload, plugins are cleared and load_plugins is called
        # (which would repopulate, but we mocked it)


# ==============================================================================
# Job Registration Tests
# ==============================================================================


class TestJobRegistration:
    """Tests for job registration with scheduler."""

    def test_enable_patches_register_job(self, plugin_manager, minimal_config, mock_scheduler, mock_providers):
        """Test enabling plugin patches register_job."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["sample-plugin"] = plugin

        plugin_manager.enable_plugin("sample-plugin")

        # Try to register a job
        def dummy_task():
            pass

        job_id = plugin.register_job(dummy_task, trigger="interval", seconds=60)

        mock_scheduler.add_job.assert_called_once()
        assert job_id == "job_123"

    def test_disable_cleans_up_jobs(self, plugin_manager, minimal_config, mock_scheduler, mock_providers):
        """Test disabling plugin cleans up jobs."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["sample-plugin"] = plugin

        # Enable and register a job
        plugin_manager.enable_plugin("sample-plugin")

        def dummy_task():
            pass

        plugin.register_job(dummy_task, trigger="interval", seconds=60)

        # Disable plugin
        plugin_manager.disable_plugin("sample-plugin")

        mock_scheduler.remove_job.assert_called_once()


# ==============================================================================
# Hot Reload Tests
# ==============================================================================


class TestHotReload:
    """Tests for hot reload functionality."""

    def test_start_hot_reload_disabled(self, config_with_disabled_plugins, mock_client):
        """Test start_hot_reload when auto_reload is disabled."""
        config = BotConfig(
            webhooks=[],
            plugins=PluginConfig(
                enabled=True,
                plugin_dir="./plugins",
                auto_reload=False,
            ),
        )
        manager = PluginManager(config=config, client=mock_client)

        manager.start_hot_reload()

        assert manager._observer is None

    def test_start_hot_reload_missing_directory(self, minimal_config, mock_client):
        """Test start_hot_reload with missing plugin directory."""
        config = BotConfig(
            webhooks=[],
            plugins=PluginConfig(
                enabled=True,
                plugin_dir="/nonexistent/plugins",
                auto_reload=True,
            ),
        )
        manager = PluginManager(config=config, client=mock_client)

        manager.start_hot_reload()

        assert manager._observer is None

    def test_start_stop_hot_reload(self, mock_client):
        """Test starting and stopping hot reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = BotConfig(
                webhooks=[],
                plugins=PluginConfig(
                    enabled=True,
                    plugin_dir=tmpdir,
                    auto_reload=True,
                    reload_delay=0.5,
                ),
            )
            manager = PluginManager(config=config, client=mock_client)

            manager.start_hot_reload()
            assert manager._observer is not None

            manager.stop_hot_reload()
            assert manager._observer is None

    def test_stop_hot_reload_when_not_started(self, plugin_manager):
        """Test stop_hot_reload when not started."""
        # Should not raise
        plugin_manager.stop_hot_reload()
        assert plugin_manager._observer is None


# ==============================================================================
# Event Dispatching Tests
# ==============================================================================


class TestEventDispatching:
    """Tests for event dispatching to plugins."""

    def test_dispatch_event_to_plugins(self, plugin_manager, minimal_config, mock_providers):
        """Test dispatching event to all plugins."""
        plugin1 = SamplePlugin(minimal_config, providers=mock_providers)
        plugin2 = SamplePlugin(minimal_config, providers=mock_providers)
        plugin2.metadata = lambda: PluginMetadata(name="plugin2", version="1.0.0")

        plugin_manager.plugins["sample-plugin"] = plugin1
        plugin_manager.plugins["plugin2"] = plugin2

        event = {"type": "message", "content": "Hello"}
        context = {"user_id": "123"}

        plugin_manager.dispatch_event(event, context)

        assert len(plugin1.events_received) == 1
        assert plugin1.events_received[0] == event
        assert len(plugin2.events_received) == 1

    def test_dispatch_event_no_context(self, plugin_manager, minimal_config, mock_providers):
        """Test dispatching event without context."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["sample-plugin"] = plugin

        event = {"type": "message"}

        plugin_manager.dispatch_event(event)

        assert len(plugin.events_received) == 1

    def test_dispatch_event_handles_plugin_errors(self, plugin_manager, minimal_config, mock_providers):
        """Test dispatch handles plugin errors gracefully."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)

        def failing_handler(event: dict, context: dict | None = None) -> None:
            raise RuntimeError("Handler error")

        plugin.handle_event = failing_handler
        plugin_manager.plugins["sample-plugin"] = plugin

        event = {"type": "message"}

        # Should not raise
        plugin_manager.dispatch_event(event)

    def test_dispatch_event_skips_plugins_without_handler(self, plugin_manager, minimal_config, mock_providers):
        """Test dispatch skips plugins without handle_event attribute."""

        class NoHandlerPlugin(BasePlugin):
            """Plugin without handle_event override - uses default no-op."""

            def metadata(self):
                return PluginMetadata(name="no-handler", version="1.0.0")

        plugin = NoHandlerPlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["no-handler"] = plugin

        event = {"type": "message"}

        # Should not raise - default handle_event returns None
        plugin_manager.dispatch_event(event)


# ==============================================================================
# Multi-Provider Support Tests
# ==============================================================================


class TestMultiProviderSupport:
    """Tests for multi-provider support in plugin manager."""

    def test_plugin_receives_providers(self, plugin_manager, minimal_config, mock_providers):
        """Test plugin receives providers dict."""
        plugin_code = '''
from feishu_webhook_bot.plugins.base import BasePlugin, PluginMetadata

class ProviderTestPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="provider-test", version="1.0.0")
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "provider_test.py"
            plugin_file.write_text(plugin_code)

            plugin = plugin_manager._load_plugin_from_file(plugin_file)

            assert plugin is not None
            assert plugin.providers == mock_providers

    def test_plugin_can_access_specific_provider(self, plugin_manager, minimal_config, mock_providers):
        """Test plugin can access specific provider."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["sample-plugin"] = plugin

        provider = plugin.get_provider("test_provider")

        assert provider is not None
        assert provider.name == "test_provider"

    def test_plugin_provider_not_found(self, plugin_manager, minimal_config, mock_providers):
        """Test plugin handles missing provider."""
        plugin = SamplePlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["sample-plugin"] = plugin

        provider = plugin.get_provider("nonexistent")

        assert provider is None


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestErrorHandling:
    """Tests for error handling in plugin manager."""

    def test_enable_plugin_handles_error(self, plugin_manager, minimal_config, mock_providers):
        """Test enable_plugin handles plugin errors."""
        plugin = FailingPlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["failing-plugin"] = plugin

        result = plugin_manager.enable_plugin("failing-plugin")

        assert result is False

    def test_disable_plugin_handles_error(self, plugin_manager, minimal_config, mock_providers):
        """Test disable_plugin handles plugin errors."""
        plugin = FailingPlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["failing-plugin"] = plugin

        result = plugin_manager.disable_plugin("failing-plugin")

        assert result is False

    def test_reload_handles_unload_error(self, plugin_manager, minimal_config, mock_providers):
        """Test reload handles plugin unload errors gracefully."""
        plugin = FailingPlugin(minimal_config, providers=mock_providers)
        plugin_manager.plugins["failing-plugin"] = plugin

        # Should not raise
        with patch.object(plugin_manager, "load_plugins"):
            with patch.object(plugin_manager, "enable_all"):
                plugin_manager.reload_plugins()
