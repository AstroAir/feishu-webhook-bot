"""Plugin configuration schema registry.

This module provides a centralized registry for plugin configuration schemas,
enabling discovery, validation, and management across the plugin system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from .base import BasePlugin
    from .config_schema import PluginConfigSchema

logger = get_logger("plugin.config_registry")


class ConfigSchemaRegistry:
    """Registry for plugin configuration schemas.

    Provides centralized management for plugin configuration schemas,
    enabling discovery and validation across the plugin system.

    This is implemented as a class with class methods to provide a
    singleton-like interface without requiring instantiation.

    Example:
        ```python
        from feishu_webhook_bot.plugins.config_registry import ConfigSchemaRegistry

        # Register a schema
        ConfigSchemaRegistry.register("my-plugin", MyPluginConfigSchema)

        # Get a schema
        schema = ConfigSchemaRegistry.get("my-plugin")
        if schema:
            is_valid, errors = schema.validate_config(config)

        # Auto-discover from plugin
        ConfigSchemaRegistry.auto_register(my_plugin_instance)
        ```
    """

    _schemas: dict[str, type[PluginConfigSchema]] = {}

    @classmethod
    def register(cls, plugin_name: str, schema: type[PluginConfigSchema]) -> None:
        """Register a configuration schema for a plugin.

        Args:
            plugin_name: Unique plugin identifier
            schema: PluginConfigSchema subclass
        """
        cls._schemas[plugin_name] = schema
        logger.debug("Registered config schema for plugin: %s", plugin_name)

    @classmethod
    def unregister(cls, plugin_name: str) -> None:
        """Unregister a plugin's schema.

        Args:
            plugin_name: Plugin identifier to unregister
        """
        if plugin_name in cls._schemas:
            del cls._schemas[plugin_name]
            logger.debug("Unregistered config schema for plugin: %s", plugin_name)

    @classmethod
    def get(cls, plugin_name: str) -> type[PluginConfigSchema] | None:
        """Get the configuration schema for a plugin.

        Args:
            plugin_name: Plugin identifier

        Returns:
            PluginConfigSchema subclass or None if not registered
        """
        return cls._schemas.get(plugin_name)

    @classmethod
    def get_all(cls) -> dict[str, type[PluginConfigSchema]]:
        """Get all registered schemas.

        Returns:
            Dictionary mapping plugin names to schema classes
        """
        return dict(cls._schemas)

    @classmethod
    def has_schema(cls, plugin_name: str) -> bool:
        """Check if a plugin has a registered schema.

        Args:
            plugin_name: Plugin identifier

        Returns:
            True if a schema is registered for this plugin
        """
        return plugin_name in cls._schemas

    @classmethod
    def discover_from_plugin(cls, plugin: BasePlugin) -> type[PluginConfigSchema] | None:
        """Discover configuration schema from a plugin instance.

        Checks for schema in the following order:
        1. `config_schema` class attribute (type)
        2. `config_schema()` class method
        3. `ConfigSchema` inner class

        Args:
            plugin: Plugin instance to inspect

        Returns:
            PluginConfigSchema subclass if found, None otherwise
        """
        from .config_schema import PluginConfigSchema

        plugin_class = plugin.__class__

        # 1. Check for config_schema class attribute
        if hasattr(plugin_class, "config_schema"):
            schema = plugin_class.config_schema
            if isinstance(schema, type) and issubclass(schema, PluginConfigSchema):
                return schema
            # It might be a classmethod
            if callable(schema):
                try:
                    result = schema()
                    if isinstance(result, type) and issubclass(result, PluginConfigSchema):
                        return result
                except Exception:
                    pass

        # 2. Check for get_config_schema method
        if hasattr(plugin_class, "get_config_schema"):
            get_schema = plugin_class.get_config_schema
            if callable(get_schema):
                try:
                    result = get_schema()
                    if isinstance(result, type) and issubclass(result, PluginConfigSchema):
                        return result
                except Exception:
                    pass

        # 3. Check for ConfigSchema inner class
        if hasattr(plugin_class, "ConfigSchema"):
            inner_class = plugin_class.ConfigSchema
            if isinstance(inner_class, type) and issubclass(inner_class, PluginConfigSchema):
                return inner_class

        return None

    @classmethod
    def auto_register(cls, plugin: BasePlugin) -> bool:
        """Automatically discover and register a plugin's schema.

        Args:
            plugin: Plugin instance to process

        Returns:
            True if a schema was found and registered
        """
        schema = cls.discover_from_plugin(plugin)
        if schema is not None:
            plugin_name = plugin.metadata().name
            cls.register(plugin_name, schema)
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Clear all registered schemas.

        This is mainly useful for testing to ensure a clean state.
        """
        cls._schemas.clear()
        logger.debug("Cleared all registered config schemas")

    @classmethod
    def get_plugin_names(cls) -> list[str]:
        """Get list of plugin names with registered schemas.

        Returns:
            List of plugin names
        """
        return list(cls._schemas.keys())

    @classmethod
    def validate_plugin_config(
        cls, plugin_name: str, config: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate configuration for a specific plugin.

        Convenience method that combines get() and validate_config().

        Args:
            plugin_name: Plugin identifier
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, list_of_errors).
            Returns (True, []) if no schema is registered.
        """
        schema = cls.get(plugin_name)
        if schema is None:
            return True, []
        return schema.validate_config(config)
