"""Tests for plugins.config_registry module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from pydantic import Field

from feishu_webhook_bot.plugins.config_registry import ConfigSchemaRegistry
from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema


class MockConfigSchema(PluginConfigSchema):
    """Mock config schema for testing."""

    api_key: str = Field(..., description="API key")
    timeout: int = Field(default=30, description="Timeout in seconds")


class AnotherMockSchema(PluginConfigSchema):
    """Another mock schema for testing."""

    url: str = Field(..., description="URL")


class TestConfigSchemaRegistry:
    """Tests for ConfigSchemaRegistry."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        ConfigSchemaRegistry.clear()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        ConfigSchemaRegistry.clear()

    def test_register_schema(self) -> None:
        """Test registering a schema."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)

        assert ConfigSchemaRegistry.has_schema("test-plugin")
        assert ConfigSchemaRegistry.get("test-plugin") is MockConfigSchema

    def test_unregister_schema(self) -> None:
        """Test unregistering a schema."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)
        ConfigSchemaRegistry.unregister("test-plugin")

        assert not ConfigSchemaRegistry.has_schema("test-plugin")
        assert ConfigSchemaRegistry.get("test-plugin") is None

    def test_unregister_nonexistent_schema(self) -> None:
        """Test unregistering a non-existent schema does not raise."""
        ConfigSchemaRegistry.unregister("nonexistent")

    def test_get_nonexistent_schema(self) -> None:
        """Test getting a non-existent schema returns None."""
        result = ConfigSchemaRegistry.get("nonexistent")

        assert result is None

    def test_get_all_schemas(self) -> None:
        """Test getting all registered schemas."""
        ConfigSchemaRegistry.register("plugin-a", MockConfigSchema)
        ConfigSchemaRegistry.register("plugin-b", AnotherMockSchema)

        all_schemas = ConfigSchemaRegistry.get_all()

        assert len(all_schemas) == 2
        assert all_schemas["plugin-a"] is MockConfigSchema
        assert all_schemas["plugin-b"] is AnotherMockSchema

    def test_has_schema(self) -> None:
        """Test has_schema method."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)

        assert ConfigSchemaRegistry.has_schema("test-plugin") is True
        assert ConfigSchemaRegistry.has_schema("other-plugin") is False

    def test_clear(self) -> None:
        """Test clearing all schemas."""
        ConfigSchemaRegistry.register("plugin-a", MockConfigSchema)
        ConfigSchemaRegistry.register("plugin-b", AnotherMockSchema)

        ConfigSchemaRegistry.clear()

        assert len(ConfigSchemaRegistry.get_all()) == 0

    def test_get_plugin_names(self) -> None:
        """Test getting list of plugin names."""
        ConfigSchemaRegistry.register("plugin-a", MockConfigSchema)
        ConfigSchemaRegistry.register("plugin-b", AnotherMockSchema)

        names = ConfigSchemaRegistry.get_plugin_names()

        assert "plugin-a" in names
        assert "plugin-b" in names
        assert len(names) == 2

    def test_validate_plugin_config_valid(self) -> None:
        """Test validating valid plugin config."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)

        is_valid, errors = ConfigSchemaRegistry.validate_plugin_config(
            "test-plugin", {"api_key": "secret123", "timeout": 60}
        )

        assert is_valid is True
        assert errors == []

    def test_validate_plugin_config_invalid(self) -> None:
        """Test validating invalid plugin config."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)

        is_valid, errors = ConfigSchemaRegistry.validate_plugin_config(
            "test-plugin", {}
        )

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_plugin_config_no_schema(self) -> None:
        """Test validating config when no schema registered."""
        is_valid, errors = ConfigSchemaRegistry.validate_plugin_config(
            "unknown-plugin", {"any": "config"}
        )

        assert is_valid is True
        assert errors == []

    def test_discover_from_plugin_with_config_schema_attribute(self) -> None:
        """Test discovering schema from plugin with config_schema attribute."""
        mock_plugin = MagicMock()
        mock_plugin.__class__.config_schema = MockConfigSchema

        schema = ConfigSchemaRegistry.discover_from_plugin(mock_plugin)

        assert schema is MockConfigSchema

    def test_discover_from_plugin_with_inner_class(self) -> None:
        """Test discovering schema from plugin with ConfigSchema inner class."""

        class PluginWithInnerSchema:
            ConfigSchema = MockConfigSchema

            def metadata(self) -> Any:
                return MagicMock(name="test-plugin", version="1.0.0")

        plugin = PluginWithInnerSchema()
        schema = ConfigSchemaRegistry.discover_from_plugin(plugin)

        assert schema is MockConfigSchema

    def test_discover_from_plugin_no_schema(self) -> None:
        """Test discovering schema from plugin without schema."""

        class PluginWithoutSchema:
            def metadata(self) -> Any:
                return MagicMock(name="test-plugin", version="1.0.0")

        plugin = PluginWithoutSchema()
        schema = ConfigSchemaRegistry.discover_from_plugin(plugin)

        assert schema is None

    def test_auto_register_success(self) -> None:
        """Test auto-registering a plugin's schema."""

        class PluginWithSchema:
            config_schema = MockConfigSchema

            def metadata(self) -> Any:
                mock = MagicMock()
                mock.name = "auto-plugin"
                return mock

        plugin = PluginWithSchema()
        result = ConfigSchemaRegistry.auto_register(plugin)

        assert result is True
        assert ConfigSchemaRegistry.has_schema("auto-plugin")
        assert ConfigSchemaRegistry.get("auto-plugin") is MockConfigSchema

    def test_auto_register_no_schema(self) -> None:
        """Test auto-registering a plugin without schema."""

        class PluginWithoutSchema:
            def metadata(self) -> Any:
                mock = MagicMock()
                mock.name = "no-schema-plugin"
                return mock

        plugin = PluginWithoutSchema()
        result = ConfigSchemaRegistry.auto_register(plugin)

        assert result is False
        assert not ConfigSchemaRegistry.has_schema("no-schema-plugin")
