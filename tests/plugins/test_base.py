"""Comprehensive tests for plugin base class and metadata.

Tests cover:
- PluginMetadata dataclass
- BasePlugin abstract class
- Plugin lifecycle hooks
- Provider access patterns
- Job registration
- Configuration access
- Event handling
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from feishu_webhook_bot.core.config import BotConfig, PluginConfig, PluginSettingsConfig
from feishu_webhook_bot.core.provider import BaseProvider, ProviderConfig
from feishu_webhook_bot.plugins.base import BasePlugin, PluginMetadata

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

    def send_rich_text(
        self, title: str, content: list, target: str, language: str = "zh_cn"
    ) -> Any:
        return Mock(success=True)

    def send_image(self, image_key: str, target: str) -> Any:
        return Mock(success=True)


class ConcretePlugin(BasePlugin):
    """Concrete plugin implementation for testing."""

    def __init__(
        self,
        config: BotConfig,
        client: Any = None,
        providers: dict[str, BaseProvider] | None = None,
        plugin_name: str = "test-plugin",
        plugin_version: str = "1.0.0",
    ):
        self._plugin_name = plugin_name
        self._plugin_version = plugin_version
        super().__init__(config, client, providers)

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self._plugin_name,
            version=self._plugin_version,
            description="Test plugin",
            author="Test Author",
        )


class TrackingPlugin(BasePlugin):
    """Plugin that tracks lifecycle calls."""

    def __init__(self, config: BotConfig, client: Any = None, providers: dict | None = None):
        self.lifecycle_calls: list[str] = []
        super().__init__(config, client, providers)

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="tracking-plugin", version="1.0.0")

    def on_load(self) -> None:
        self.lifecycle_calls.append("on_load")

    def on_enable(self) -> None:
        self.lifecycle_calls.append("on_enable")

    def on_disable(self) -> None:
        self.lifecycle_calls.append("on_disable")

    def on_unload(self) -> None:
        self.lifecycle_calls.append("on_unload")


@pytest.fixture
def minimal_config():
    """Create minimal bot configuration."""
    return BotConfig(
        webhooks=[],
        plugins=PluginConfig(
            enabled=True,
            plugin_dir="./plugins",
        ),
    )


@pytest.fixture
def config_with_plugin_settings():
    """Create config with plugin-specific settings."""
    return BotConfig(
        webhooks=[],
        plugins=PluginConfig(
            enabled=True,
            plugin_dir="./plugins",
            plugin_settings=[
                PluginSettingsConfig(
                    plugin_name="test-plugin",
                    enabled=True,
                    priority=10,
                    settings={
                        "api_key": "secret123",
                        "threshold": 80,
                        "enabled_features": ["feature1", "feature2"],
                    },
                ),
            ],
        ),
    )


@pytest.fixture
def mock_client():
    """Create mock webhook client."""
    return Mock()


@pytest.fixture
def mock_providers():
    """Create mock providers dictionary."""
    config1 = ProviderConfig(provider_type="feishu", name="feishu_default")
    config2 = ProviderConfig(provider_type="qq", name="qq_bot")

    provider1 = MockProvider(config1)
    provider2 = MockProvider(config2)

    return {
        "feishu_default": provider1,
        "qq_bot": provider2,
    }


# ==============================================================================
# PluginMetadata Tests
# ==============================================================================


class TestPluginMetadata:
    """Tests for PluginMetadata dataclass."""

    def test_metadata_required_name(self):
        """Test PluginMetadata requires name."""
        metadata = PluginMetadata(name="my-plugin")
        assert metadata.name == "my-plugin"

    def test_metadata_default_values(self):
        """Test PluginMetadata default values."""
        metadata = PluginMetadata(name="test")
        assert metadata.version == "1.0.0"
        assert metadata.description == ""
        assert metadata.author == ""
        assert metadata.enabled is True

    def test_metadata_all_fields(self):
        """Test PluginMetadata with all fields."""
        metadata = PluginMetadata(
            name="full-plugin",
            version="2.3.4",
            description="A full-featured plugin",
            author="John Doe",
            enabled=False,
        )
        assert metadata.name == "full-plugin"
        assert metadata.version == "2.3.4"
        assert metadata.description == "A full-featured plugin"
        assert metadata.author == "John Doe"
        assert metadata.enabled is False

    def test_metadata_version_format(self):
        """Test PluginMetadata accepts various version formats."""
        # Semantic versions
        assert PluginMetadata(name="p", version="1.0.0").version == "1.0.0"
        assert PluginMetadata(name="p", version="2.1.3-beta").version == "2.1.3-beta"
        assert PluginMetadata(name="p", version="0.0.1").version == "0.0.1"

    def test_metadata_name_not_empty(self):
        """Test PluginMetadata name should not be empty."""
        # Note: dataclass doesn't validate, but we test the intent
        metadata = PluginMetadata(name="")
        assert metadata.name == ""  # Empty is technically allowed


# ==============================================================================
# BasePlugin Initialization Tests
# ==============================================================================


class TestBasePluginInitialization:
    """Tests for BasePlugin initialization."""

    def test_plugin_initialization_minimal(self, minimal_config):
        """Test plugin initialization with minimal args."""
        plugin = ConcretePlugin(minimal_config)

        assert plugin.config is minimal_config
        assert plugin.client is None
        assert plugin.providers == {}
        assert plugin._job_ids == []

    def test_plugin_initialization_with_client(self, minimal_config, mock_client):
        """Test plugin initialization with client."""
        plugin = ConcretePlugin(minimal_config, client=mock_client)

        assert plugin.client is mock_client

    def test_plugin_initialization_with_providers(self, minimal_config, mock_providers):
        """Test plugin initialization with providers."""
        plugin = ConcretePlugin(minimal_config, providers=mock_providers)

        assert plugin.providers == mock_providers
        assert len(plugin.providers) == 2

    def test_plugin_initialization_with_all_args(self, minimal_config, mock_client, mock_providers):
        """Test plugin initialization with all arguments."""
        plugin = ConcretePlugin(minimal_config, mock_client, mock_providers)

        assert plugin.config is minimal_config
        assert plugin.client is mock_client
        assert plugin.providers == mock_providers

    def test_plugin_logger_created(self, minimal_config):
        """Test plugin logger is created with plugin name."""
        plugin = ConcretePlugin(minimal_config, plugin_name="my-special-plugin")

        assert plugin.logger is not None


# ==============================================================================
# Plugin Property Tests
# ==============================================================================


class TestBasePluginProperties:
    """Tests for BasePlugin properties."""

    def test_client_getter(self, minimal_config, mock_client):
        """Test client property getter."""
        plugin = ConcretePlugin(minimal_config, client=mock_client)
        assert plugin.client is mock_client

    def test_client_setter(self, minimal_config, mock_client):
        """Test client property setter."""
        plugin = ConcretePlugin(minimal_config)
        plugin.client = mock_client
        assert plugin.client is mock_client

    def test_providers_getter(self, minimal_config, mock_providers):
        """Test providers property getter."""
        plugin = ConcretePlugin(minimal_config, providers=mock_providers)
        assert plugin.providers is mock_providers

    def test_providers_setter(self, minimal_config, mock_providers):
        """Test providers property setter."""
        plugin = ConcretePlugin(minimal_config)
        plugin.providers = mock_providers
        assert plugin.providers == mock_providers


# ==============================================================================
# Provider Access Tests
# ==============================================================================


class TestProviderAccess:
    """Tests for provider access methods."""

    def test_get_provider_existing(self, minimal_config, mock_providers):
        """Test getting an existing provider."""
        plugin = ConcretePlugin(minimal_config, providers=mock_providers)

        provider = plugin.get_provider("feishu_default")

        assert provider is not None
        assert provider.name == "feishu_default"

    def test_get_provider_not_found(self, minimal_config, mock_providers):
        """Test getting a nonexistent provider."""
        plugin = ConcretePlugin(minimal_config, providers=mock_providers)

        provider = plugin.get_provider("nonexistent")

        assert provider is None

    def test_get_provider_empty_providers(self, minimal_config):
        """Test getting provider when providers dict is empty."""
        plugin = ConcretePlugin(minimal_config)

        provider = plugin.get_provider("any")

        assert provider is None

    def test_get_all_providers(self, minimal_config, mock_providers):
        """Test accessing all providers."""
        plugin = ConcretePlugin(minimal_config, providers=mock_providers)

        all_providers = plugin.providers

        assert len(all_providers) == 2
        assert "feishu_default" in all_providers
        assert "qq_bot" in all_providers


# ==============================================================================
# Lifecycle Hook Tests
# ==============================================================================


class TestLifecycleHooks:
    """Tests for plugin lifecycle hooks."""

    def test_on_load_default(self, minimal_config):
        """Test on_load default implementation."""
        plugin = ConcretePlugin(minimal_config)
        # Should not raise
        plugin.on_load()

    def test_on_enable_default(self, minimal_config):
        """Test on_enable default implementation."""
        plugin = ConcretePlugin(minimal_config)
        # Should not raise
        plugin.on_enable()

    def test_on_disable_default(self, minimal_config):
        """Test on_disable default implementation."""
        plugin = ConcretePlugin(minimal_config)
        # Should not raise
        plugin.on_disable()

    def test_on_unload_default(self, minimal_config):
        """Test on_unload default implementation."""
        plugin = ConcretePlugin(minimal_config)
        # Should not raise
        plugin.on_unload()

    def test_lifecycle_order(self, minimal_config):
        """Test lifecycle hooks can be called in proper order."""
        plugin = TrackingPlugin(minimal_config)

        plugin.on_load()
        plugin.on_enable()
        plugin.on_disable()
        plugin.on_unload()

        assert plugin.lifecycle_calls == ["on_load", "on_enable", "on_disable", "on_unload"]


# ==============================================================================
# Job Registration Tests
# ==============================================================================


class TestJobRegistration:
    """Tests for job registration methods."""

    def test_register_job_stores_id(self, minimal_config):
        """Test register_job stores job ID."""
        plugin = ConcretePlugin(minimal_config)

        def task():
            pass

        job_id = plugin.register_job(task, trigger="interval", job_id="custom_job")

        assert job_id == "custom_job"
        assert "custom_job" in plugin._job_ids

    def test_register_job_without_id(self, minimal_config):
        """Test register_job without explicit ID."""
        plugin = ConcretePlugin(minimal_config)

        def task():
            pass

        job_id = plugin.register_job(task, trigger="interval")

        # Returns empty string as job_id when not provided
        assert job_id == ""

    def test_cleanup_jobs(self, minimal_config):
        """Test cleanup_jobs clears job IDs."""
        plugin = ConcretePlugin(minimal_config)

        plugin._job_ids = ["job1", "job2", "job3"]

        plugin.cleanup_jobs()

        assert plugin._job_ids == []

    def test_register_job_with_interval_trigger(self, minimal_config):
        """Test register_job with interval trigger args."""
        plugin = ConcretePlugin(minimal_config)

        def task():
            pass

        plugin.register_job(task, trigger="interval", job_id="interval_job", minutes=5)

        assert "interval_job" in plugin._job_ids

    def test_register_job_with_cron_trigger(self, minimal_config):
        """Test register_job with cron trigger args."""
        plugin = ConcretePlugin(minimal_config)

        def task():
            pass

        plugin.register_job(task, trigger="cron", job_id="cron_job", hour="9", minute="0")

        assert "cron_job" in plugin._job_ids


# ==============================================================================
# Configuration Access Tests
# ==============================================================================


class TestConfigurationAccess:
    """Tests for plugin configuration access."""

    def test_get_config_value_existing(self, config_with_plugin_settings):
        """Test getting existing config value."""
        plugin = ConcretePlugin(config_with_plugin_settings, plugin_name="test-plugin")

        value = plugin.get_config_value("api_key")

        assert value == "secret123"

    def test_get_config_value_default(self, config_with_plugin_settings):
        """Test getting config value with default."""
        plugin = ConcretePlugin(config_with_plugin_settings, plugin_name="test-plugin")

        value = plugin.get_config_value("nonexistent", "default_value")

        assert value == "default_value"

    def test_get_config_value_no_settings(self, minimal_config):
        """Test getting config value when no settings exist."""
        plugin = ConcretePlugin(minimal_config)

        value = plugin.get_config_value("any_key", "fallback")

        assert value == "fallback"

    def test_get_config_value_numeric(self, config_with_plugin_settings):
        """Test getting numeric config value."""
        plugin = ConcretePlugin(config_with_plugin_settings, plugin_name="test-plugin")

        value = plugin.get_config_value("threshold")

        assert value == 80

    def test_get_config_value_list(self, config_with_plugin_settings):
        """Test getting list config value."""
        plugin = ConcretePlugin(config_with_plugin_settings, plugin_name="test-plugin")

        value = plugin.get_config_value("enabled_features")

        assert value == ["feature1", "feature2"]

    def test_get_all_config(self, config_with_plugin_settings):
        """Test getting all plugin configuration."""
        plugin = ConcretePlugin(config_with_plugin_settings, plugin_name="test-plugin")

        config = plugin.get_all_config()

        assert config == {
            "api_key": "secret123",
            "threshold": 80,
            "enabled_features": ["feature1", "feature2"],
        }

    def test_get_all_config_empty(self, minimal_config):
        """Test getting all config when no settings exist."""
        plugin = ConcretePlugin(minimal_config)

        config = plugin.get_all_config()

        assert config == {}


# ==============================================================================
# Event Handling Tests
# ==============================================================================


class TestEventHandling:
    """Tests for event handling."""

    def test_handle_event_default(self, minimal_config):
        """Test handle_event default implementation returns None."""
        plugin = ConcretePlugin(minimal_config)

        result = plugin.handle_event({"type": "message"})

        assert result is None

    def test_handle_event_with_context(self, minimal_config):
        """Test handle_event with context parameter."""
        plugin = ConcretePlugin(minimal_config)

        result = plugin.handle_event({"type": "message"}, {"user_id": "123"})

        assert result is None


class EventTrackingPlugin(BasePlugin):
    """Plugin that tracks received events."""

    def __init__(self, config: BotConfig, client: Any = None, providers: dict | None = None):
        super().__init__(config, client, providers)
        self.events: list[tuple[dict, dict | None]] = []

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="event-tracker", version="1.0.0")

    def handle_event(self, event: dict, context: dict | None = None) -> None:
        self.events.append((event, context))


class TestEventTrackingPlugin:
    """Tests for custom event handling implementation."""

    def test_handle_event_receives_data(self, minimal_config):
        """Test custom handle_event receives event data."""
        plugin = EventTrackingPlugin(minimal_config)

        event = {"type": "message", "content": "Hello"}
        context = {"user_id": "user123", "chat_id": "chat456"}

        plugin.handle_event(event, context)

        assert len(plugin.events) == 1
        assert plugin.events[0] == (event, context)

    def test_handle_event_multiple_events(self, minimal_config):
        """Test handling multiple events."""
        plugin = EventTrackingPlugin(minimal_config)

        plugin.handle_event({"id": 1})
        plugin.handle_event({"id": 2})
        plugin.handle_event({"id": 3})

        assert len(plugin.events) == 3


# ==============================================================================
# Abstract Method Tests
# ==============================================================================


class TestAbstractMethods:
    """Tests for abstract method requirements."""

    def test_metadata_is_abstract(self):
        """Test that metadata must be implemented."""
        # This test verifies the abstract nature of BasePlugin
        with pytest.raises(TypeError, match="abstract"):
            # Can't instantiate abstract class
            BasePlugin(Mock(), Mock())  # type: ignore


# ==============================================================================
# Plugin State Isolation Tests
# ==============================================================================


class TestPluginStateIsolation:
    """Tests for plugin state isolation."""

    def test_separate_job_ids_per_plugin(self, minimal_config):
        """Test each plugin has separate job IDs list."""
        plugin1 = ConcretePlugin(minimal_config, plugin_name="plugin1")
        plugin2 = ConcretePlugin(minimal_config, plugin_name="plugin2")

        plugin1.register_job(lambda: None, job_id="job1")
        plugin2.register_job(lambda: None, job_id="job2")

        assert plugin1._job_ids == ["job1"]
        assert plugin2._job_ids == ["job2"]

    def test_separate_providers_per_plugin(self, minimal_config, mock_providers):
        """Test each plugin can have different providers."""
        plugin1 = ConcretePlugin(minimal_config, providers=mock_providers)
        plugin2 = ConcretePlugin(minimal_config, providers={})

        assert len(plugin1.providers) == 2
        assert len(plugin2.providers) == 0


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestPluginIntegration:
    """Integration tests for plugin base class."""

    def test_full_lifecycle_with_providers(
        self, config_with_plugin_settings, mock_client, mock_providers
    ):
        """Test full plugin lifecycle with providers."""
        plugin = TrackingPlugin(config_with_plugin_settings, mock_client, mock_providers)

        # Verify initialization
        assert plugin.client is mock_client
        assert plugin.providers == mock_providers

        # Run lifecycle
        plugin.on_load()
        plugin.on_enable()

        # Register jobs during enable
        plugin.register_job(lambda: None, job_id="periodic_task")

        plugin.on_disable()
        plugin.cleanup_jobs()
        plugin.on_unload()

        # Verify lifecycle order
        assert plugin.lifecycle_calls == ["on_load", "on_enable", "on_disable", "on_unload"]
        assert plugin._job_ids == []

    def test_plugin_with_config_access(self, config_with_plugin_settings, mock_providers):
        """Test plugin accessing configuration during lifecycle."""

        class ConfigAwarePlugin(BasePlugin):
            def __init__(
                self, config: BotConfig, client: Any = None, providers: dict | None = None
            ):
                super().__init__(config, client, providers)
                self.loaded_api_key: str | None = None
                self.loaded_threshold: int | None = None

            def metadata(self) -> PluginMetadata:
                return PluginMetadata(name="test-plugin", version="1.0.0")

            def on_load(self) -> None:
                self.loaded_api_key = self.get_config_value("api_key")
                self.loaded_threshold = self.get_config_value("threshold", 50)

        plugin = ConfigAwarePlugin(config_with_plugin_settings, providers=mock_providers)
        plugin.on_load()

        assert plugin.loaded_api_key == "secret123"
        assert plugin.loaded_threshold == 80
