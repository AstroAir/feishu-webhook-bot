"""Plugin configuration updater.

This module provides tools for safely updating YAML configuration files
while preserving comments and formatting.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from .config_schema import PluginConfigSchema

logger = get_logger("plugin.config_updater")


class ConfigUpdater:
    """Safely updates YAML configuration files preserving structure and comments.

    This class uses ruamel.yaml to preserve:
    - Comments in the YAML file
    - Original formatting and indentation
    - Key ordering

    Example:
        ```python
        updater = ConfigUpdater("config.yaml")

        # Update plugin settings
        updater.update_plugin_settings("my-plugin", {
            "api_key": "secret123",
            "timeout": 30,
        })

        # Generate template with comments
        updater.add_plugin_template("my-plugin", MyPluginConfigSchema)
        ```
    """

    def __init__(self, config_path: str | Path):
        """Initialize the config updater.

        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self._yaml = self._create_yaml_instance()

    def _create_yaml_instance(self) -> Any:
        """Create and configure ruamel.yaml instance.

        Returns:
            Configured YAML instance
        """
        try:
            from ruamel.yaml import YAML

            yaml = YAML()
            yaml.preserve_quotes = True
            yaml.default_flow_style = False
            yaml.indent(mapping=2, sequence=4, offset=2)
            return yaml
        except ImportError:
            logger.warning(
                "ruamel.yaml not installed, falling back to PyYAML. "
                "Comments will not be preserved. Install with: pip install ruamel.yaml"
            )
            return None

    def backup(self) -> Path:
        """Create a backup of the current configuration.

        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config_path.with_suffix(f".{timestamp}.backup.yaml")
        shutil.copy2(self.config_path, backup_path)
        logger.info("Created backup: %s", backup_path)
        return backup_path

    def update_plugin_settings(
        self,
        plugin_name: str,
        settings: dict[str, Any],
        create_backup: bool = True,
    ) -> None:
        """Update settings for a specific plugin.

        This method:
        1. Creates a backup if requested
        2. Loads the existing config preserving comments
        3. Ensures the plugins section exists
        4. Finds or creates the plugin entry
        5. Merges the new settings
        6. Writes back to the file

        Args:
            plugin_name: Name of the plugin
            settings: New settings to merge
            create_backup: Whether to create a backup before updating
        """
        if create_backup and self.config_path.exists():
            self.backup()

        config = self._load_config()

        # Ensure plugins section exists
        self._ensure_plugins_section(config)

        # Find or create plugin entry
        plugin_entry = self._find_plugin_entry(config["plugins"]["plugin_settings"], plugin_name)

        if plugin_entry is None:
            # Create new entry
            plugin_entry = {
                "plugin_name": plugin_name,
                "enabled": True,
                "settings": {},
            }
            config["plugins"]["plugin_settings"].append(plugin_entry)

        # Ensure settings dict exists
        if "settings" not in plugin_entry:
            plugin_entry["settings"] = {}

        # Merge new settings
        plugin_entry["settings"].update(settings)

        # Write back
        self._save_config(config)
        logger.info("Updated configuration for plugin: %s", plugin_name)

    def add_plugin_template(
        self,
        plugin_name: str,
        schema: type[PluginConfigSchema],
        include_comments: bool = True,
    ) -> None:
        """Add a plugin configuration template with comments.

        Generates a well-documented configuration section for a plugin
        using field descriptions from the schema.

        Args:
            plugin_name: Name of the plugin
            schema: Configuration schema class
            include_comments: Whether to include field descriptions as comments
        """
        template = schema.generate_template()

        if include_comments and self._yaml is not None:
            # Add comments using ruamel.yaml
            commented_template = self._add_field_comments(template, schema)
            self.update_plugin_settings(plugin_name, commented_template, create_backup=True)
        else:
            self.update_plugin_settings(plugin_name, template, create_backup=True)

    def remove_plugin_settings(self, plugin_name: str) -> bool:
        """Remove a plugin's settings from the configuration.

        Args:
            plugin_name: Name of the plugin to remove

        Returns:
            True if plugin was found and removed
        """
        config = self._load_config()

        if "plugins" not in config or "plugin_settings" not in config["plugins"]:
            return False

        plugin_settings = config["plugins"]["plugin_settings"]
        for i, entry in enumerate(plugin_settings):
            if entry.get("plugin_name") == plugin_name:
                self.backup()
                del plugin_settings[i]
                self._save_config(config)
                logger.info("Removed configuration for plugin: %s", plugin_name)
                return True

        return False

    def get_plugin_settings(self, plugin_name: str) -> dict[str, Any]:
        """Get current settings for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin settings dictionary, or empty dict if not found
        """
        config = self._load_config()

        if "plugins" not in config or "plugin_settings" not in config["plugins"]:
            return {}

        entry = self._find_plugin_entry(config["plugins"]["plugin_settings"], plugin_name)
        if entry and "settings" in entry:
            return dict(entry["settings"])
        return {}

    def list_configured_plugins(self) -> list[str]:
        """List all plugins that have configuration entries.

        Returns:
            List of plugin names
        """
        config = self._load_config()

        if "plugins" not in config or "plugin_settings" not in config["plugins"]:
            return []

        return [
            entry.get("plugin_name", "")
            for entry in config["plugins"]["plugin_settings"]
            if entry.get("plugin_name")
        ]

    def _load_config(self) -> dict[str, Any]:
        """Load the configuration file.

        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            return {}

        if self._yaml is not None:
            # Use ruamel.yaml
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = self._yaml.load(f)
                return config if config else {}
        else:
            # Fallback to PyYAML
            import yaml

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config if config else {}

    def _save_config(self, config: dict[str, Any]) -> None:
        """Save the configuration file.

        Args:
            config: Configuration dictionary to save
        """
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        if self._yaml is not None:
            # Use ruamel.yaml
            with open(self.config_path, "w", encoding="utf-8") as f:
                self._yaml.dump(config, f)
        else:
            # Fallback to PyYAML
            import yaml

            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def _ensure_plugins_section(self, config: dict[str, Any]) -> None:
        """Ensure plugins and plugin_settings sections exist.

        Args:
            config: Configuration dictionary to modify
        """
        if "plugins" not in config:
            config["plugins"] = {}
        if "plugin_settings" not in config["plugins"]:
            config["plugins"]["plugin_settings"] = []

    def _find_plugin_entry(
        self, plugin_settings: list[dict[str, Any]], plugin_name: str
    ) -> dict[str, Any] | None:
        """Find plugin entry in plugin_settings list.

        Args:
            plugin_settings: List of plugin setting entries
            plugin_name: Name of plugin to find

        Returns:
            Plugin entry dictionary or None if not found
        """
        for entry in plugin_settings:
            if entry.get("plugin_name") == plugin_name:
                return entry
        return None

    def _add_field_comments(
        self, template: dict[str, Any], schema: type[PluginConfigSchema]
    ) -> dict[str, Any]:
        """Add YAML comments based on field descriptions.

        Args:
            template: Template dictionary
            schema: Configuration schema class

        Returns:
            CommentedMap with comments added
        """
        try:
            from ruamel.yaml.comments import CommentedMap

            result = CommentedMap()
            fields = schema.get_schema_fields()

            for key, value in template.items():
                result[key] = value

                if key in fields:
                    field_def = fields[key]
                    comment_parts = []

                    if field_def.description:
                        comment_parts.append(field_def.description)
                    if field_def.example:
                        comment_parts.append(f"Example: {field_def.example}")
                    if field_def.env_var:
                        comment_parts.append(f"Env: {field_def.env_var}")
                    if field_def.required:
                        comment_parts.append("(required)")

                    if comment_parts:
                        comment = " | ".join(comment_parts)
                        result.yaml_add_eol_comment(f" {comment}", key)

            return result
        except ImportError:
            return template

    def generate_template_string(
        self, plugin_name: str, schema: type[PluginConfigSchema]
    ) -> str:
        """Generate a YAML template string for a plugin.

        This is useful for displaying to users without modifying the config file.

        Args:
            plugin_name: Name of the plugin
            schema: Configuration schema class

        Returns:
            YAML string with template configuration
        """
        import io

        template = schema.generate_template()

        # Build the full structure
        config_section = {
            "plugins": {
                "plugin_settings": [
                    {
                        "plugin_name": plugin_name,
                        "enabled": True,
                        "settings": template,
                    }
                ]
            }
        }

        if self._yaml is not None:
            output = io.StringIO()
            self._yaml.dump(config_section, output)
            return output.getvalue()
        else:
            import yaml

            return yaml.dump(config_section, default_flow_style=False, allow_unicode=True)
