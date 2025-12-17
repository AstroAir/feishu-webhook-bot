"""Plugin manager for loading, managing, and hot-reloading plugins."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ..core.client import FeishuWebhookClient
from ..core.config import BotConfig
from ..core.logger import get_logger
from ..core.provider import BaseProvider
from .base import BasePlugin

logger = get_logger("plugin_manager")


@dataclass
class PluginInfo:
    """Detailed information about a loaded plugin.

    Attributes:
        name: Plugin name
        version: Plugin version
        description: Plugin description
        author: Plugin author
        enabled: Whether plugin is currently enabled
        file_path: Path to the plugin file
        config: Current plugin configuration
        has_schema: Whether plugin has a configuration schema
        jobs: List of registered job IDs
        load_time: Timestamp when plugin was loaded
        permissions: List of required permissions
        permissions_granted: Whether all permissions are granted
    """

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    enabled: bool = True
    file_path: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    has_schema: bool = False
    jobs: list[str] = field(default_factory=list)
    load_time: float = 0.0
    permissions: list[str] = field(default_factory=list)
    permissions_granted: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "file_path": self.file_path,
            "config": self.config,
            "has_schema": self.has_schema,
            "jobs": self.jobs,
            "load_time": self.load_time,
            "permissions": self.permissions,
            "permissions_granted": self.permissions_granted,
        }


class PluginFileHandler(FileSystemEventHandler):
    """File system event handler for plugin hot-reload."""

    def __init__(self, manager: PluginManager, delay: float = 1.0):
        """Initialize the handler.

        Args:
            manager: Plugin manager instance
            delay: Delay before reloading (to debounce multiple events)
        """
        self.manager = manager
        self.delay = delay
        self._pending_reload = False
        self._last_event_time = 0.0

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Only watch Python files
        if not str(event.src_path).endswith(".py"):
            return

        current_time = time.time()
        if current_time - self._last_event_time < self.delay:
            return

        self._last_event_time = current_time
        logger.info(f"Plugin file changed: {event.src_path}")

        # Reload plugins after delay
        self.manager.reload_plugins()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory or not str(event.src_path).endswith(".py"):
            return
        current_time = time.time()
        # Debounce creation events to avoid duplicate reloads (create -> mod)
        if current_time - self._last_event_time < self.delay:
            return
        self._last_event_time = current_time
        logger.info(f"New plugin file detected: {event.src_path}")
        self.manager.reload_plugins()

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if event.is_directory or not str(event.src_path).endswith(".py"):
            return
        logger.info(f"Plugin file deleted: {event.src_path}")
        self.manager.reload_plugins()


class PluginManager:
    """Manager for loading and managing plugins.

    The plugin manager handles:
    - Plugin discovery and loading
    - Plugin lifecycle management
    - Hot-reloading of plugins
    - Job registration for plugins

    Example:
        ```python
        from feishu_webhook_bot.plugins import PluginManager

        manager = PluginManager(config, client, scheduler)
        manager.load_plugins()
        manager.enable_all()

        # Later, when shutting down
        manager.disable_all()
        ```
    """

    def __init__(
        self,
        config: BotConfig,
        client: FeishuWebhookClient | BaseProvider | None = None,
        scheduler: Any = None,
        providers: dict[str, BaseProvider] | None = None,
    ):
        """Initialize the plugin manager.

        Args:
            config: Bot configuration
            client: Default webhook client or provider (backward compatible)
            scheduler: Task scheduler instance (optional)
            providers: Dict of all available providers (new multi-provider support)
        """
        self.config = config
        self.client = client
        self.scheduler = scheduler
        self.providers: dict[str, BaseProvider] = providers or {}
        self.plugins: dict[str, BasePlugin] = {}
        self._plugin_files: dict[str, Path] = {}  # Map plugin name to file path
        self._plugin_enabled: dict[str, bool] = {}  # Track enabled state
        self._plugin_load_times: dict[str, float] = {}  # Track load times
        self._observer: Observer | None = None

        # Permission and sandbox management
        self._permission_manager = None
        self._sandbox = None
        self._sandbox_enabled = getattr(config.plugins, "sandbox_enabled", False)

    def _discover_plugins(self, plugin_dir: Path) -> list[Path]:
        """Discover plugin files in the plugin directory.

        Args:
            plugin_dir: Directory to search for plugins

        Returns:
            List of plugin file paths
        """
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return []

        plugin_files = []
        for path in plugin_dir.glob("*.py"):
            if path.name.startswith("_"):
                continue
            plugin_files.append(path)

        logger.info(f"Discovered {len(plugin_files)} plugin files")
        return plugin_files

    def _load_plugin_from_file(self, file_path: Path) -> BasePlugin | None:
        """Load a plugin from a Python file.

        Args:
            file_path: Path to plugin file

        Returns:
            Plugin instance or None if loading failed
        """
        try:
            # Generate module name
            module_name = f"feishu_bot_plugin_{file_path.stem}"

            # If module already loaded, try to reload it. If the existing
            # module has no spec (can happen for modules loaded from a
            # previous dynamic import), remove it and load fresh.
            if module_name in sys.modules:
                # Always drop the previous module to avoid reload issues when
                # specs are missing (common with dynamically loaded modules
                # under test environments).
                del sys.modules[module_name]

            # Load module from file
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load spec for plugin: {file_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find plugin class (subclass of BasePlugin)
            plugin_class = None
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BasePlugin)
                    and obj is not BasePlugin
                    and obj.__module__ == module_name
                ):
                    plugin_class = obj
                    break

            if plugin_class is None:
                logger.error(f"No plugin class found in: {file_path}")
                return None

            # Instantiate plugin with both client and providers for compatibility
            plugin = plugin_class(self.config, self.client, self.providers)
            plugin_name = plugin.metadata().name
            self._plugin_files[plugin_name] = file_path
            self._plugin_load_times[plugin_name] = time.time()
            logger.info(f"Loaded plugin: {plugin_name} from {file_path.name}")
            return plugin

        except Exception as e:
            logger.error(f"Error loading plugin from {file_path}: {e}", exc_info=True)
            return None

    def load_plugins(self) -> None:
        """Discover and load all plugins from the plugin directory."""
        if not self.config.plugins.enabled:
            logger.info("Plugin system is disabled")
            return

        plugin_dir = Path(self.config.plugins.plugin_dir)
        plugin_files = self._discover_plugins(plugin_dir)

        # Sort plugins by priority if configured
        plugin_priorities: dict[str, int] = {}
        for plugin_setting in self.config.plugins.plugin_settings:
            plugin_priorities[plugin_setting.plugin_name] = plugin_setting.priority

        # Load plugins
        loaded_plugins: list[tuple[str, BasePlugin, int]] = []
        for file_path in plugin_files:
            plugin = self._load_plugin_from_file(file_path)
            if plugin:
                metadata = plugin.metadata()

                # Check if plugin is disabled in configuration
                plugin_enabled = True
                for plugin_setting in self.config.plugins.plugin_settings:
                    if plugin_setting.plugin_name == metadata.name:
                        plugin_enabled = plugin_setting.enabled
                        break

                if not plugin_enabled:
                    logger.info(f"Plugin {metadata.name} is disabled in configuration")
                    continue

                priority = plugin_priorities.get(metadata.name, 100)
                loaded_plugins.append((metadata.name, plugin, priority))

        # Sort by priority (lower numbers first)
        loaded_plugins.sort(key=lambda x: x[2])

        # Register plugins in priority order
        for name, plugin, _ in loaded_plugins:
            self.plugins[name] = plugin
            self._plugin_enabled[name] = False  # Not enabled until on_enable called
            plugin.on_load()
            # Register and auto-grant permissions
            self.register_plugin_permissions(name)
            logger.info(f"Loaded plugin: {name}")

        logger.info(f"Loaded {len(self.plugins)} plugins")

    def reload_plugins(self) -> None:
        """Reload all plugins (for hot-reload)."""
        logger.info("Reloading plugins...")

        # Disable and unload existing plugins
        for plugin in self.plugins.values():
            try:
                plugin.on_disable()
                plugin.on_unload()
                plugin.cleanup_jobs()
            except Exception as e:
                logger.error(f"Error unloading plugin {plugin.metadata().name}: {e}")

        # Clear plugin dict
        self.plugins.clear()

        # Reload plugins
        self.load_plugins()

        # Re-enable plugins
        self.enable_all()

        logger.info("Plugin reload complete")

    def enable_plugin(self, name: str) -> bool:
        """Enable a specific plugin.

        Args:
            name: Plugin name

        Returns:
            True if plugin was enabled, False otherwise
        """
        plugin = self.plugins.get(name)
        if not plugin:
            logger.warning(f"Plugin not found: {name}")
            return False

        try:
            # Patch register_job to actually register with scheduler
            if self.scheduler:

                def patched_register(
                    func: Any,
                    trigger: str = "interval",
                    job_id: str | None = None,
                    **trigger_args: Any,
                ) -> str:
                    if job_id is None:
                        job_id = f"plugin.{name}.{func.__name__}"
                    actual_job_id = self.scheduler.add_job(
                        func, trigger=trigger, job_id=job_id, **trigger_args
                    )
                    plugin._job_ids.append(actual_job_id)
                    return actual_job_id

                plugin.register_job = patched_register  # type: ignore

                # Patch cleanup to remove jobs from the scheduler when the
                # plugin is disabled.
                def patched_cleanup() -> None:
                    try:
                        for jid in list(plugin._job_ids):
                            try:
                                self.scheduler.remove_job(jid)
                            except Exception:
                                logger.exception("Failed to remove job %s", jid)
                        plugin._job_ids.clear()
                    except Exception as e:
                        logger.error("Error during plugin cleanup: %s", e)

                plugin.cleanup_jobs = patched_cleanup  # type: ignore

            plugin.on_enable()
            self._plugin_enabled[name] = True
            logger.info(f"Plugin enabled: {name}")
            return True

        except Exception as e:
            logger.error(f"Error enabling plugin {name}: {e}", exc_info=True)
            return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a specific plugin.

        Args:
            name: Plugin name

        Returns:
            True if plugin was disabled, False otherwise
        """
        plugin = self.plugins.get(name)
        if not plugin:
            logger.warning(f"Plugin not found: {name}")
            return False

        try:
            plugin.on_disable()
            plugin.cleanup_jobs()
            self._plugin_enabled[name] = False
            logger.info(f"Plugin disabled: {name}")
            return True

        except Exception as e:
            logger.error(f"Error disabling plugin {name}: {e}", exc_info=True)
            return False

    def enable_all(self) -> None:
        """Enable all loaded plugins."""
        for name in self.plugins:
            self.enable_plugin(name)

    def disable_all(self) -> None:
        """Disable all loaded plugins."""
        for name in self.plugins:
            self.disable_plugin(name)

    def get_plugin(self, name: str) -> BasePlugin | None:
        """Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None
        """
        return self.plugins.get(name)

    def list_plugins(self) -> list[str]:
        """Get list of loaded plugin names.

        Returns:
            List of plugin names
        """
        return list(self.plugins.keys())

    def start_hot_reload(self) -> None:
        """Start watching for plugin file changes."""
        if not self.config.plugins.auto_reload:
            logger.info("Hot reload is disabled")
            return

        plugin_dir = Path(self.config.plugins.plugin_dir)
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return

        event_handler = PluginFileHandler(self, delay=self.config.plugins.reload_delay)
        observer = Observer()
        observer.schedule(event_handler, str(plugin_dir), recursive=False)
        observer.start()
        self._observer = observer

        logger.info(f"Hot reload enabled for: {plugin_dir}")

    def stop_hot_reload(self) -> None:
        """Stop watching for plugin file changes."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Hot reload stopped")

    def dispatch_event(self, event: dict[str, Any], context: dict[str, Any] | None = None) -> None:
        """Forward an inbound event to all loaded plugins.

        This method dispatches events to plugins in two ways:
        1. Generic handle_event() for all events
        2. QQ-specific handlers (handle_qq_notice, handle_qq_request, handle_qq_message)
           for OneBot11/Napcat events
        """
        post_type = event.get("post_type", "")

        for plugin in self.plugins.values():
            # 1. Generic event handler
            handler = getattr(plugin, "handle_event", None)
            if handler:
                try:
                    handler(event, context or {})
                except Exception as exc:
                    metadata = plugin.metadata()
                    logger.error(
                        "Plugin '%s' failed to handle event: %s",
                        metadata.name,
                        exc,
                        exc_info=True,
                    )

            # 2. QQ-specific handlers for OneBot11 events
            if post_type == "notice":
                self._dispatch_qq_notice(plugin, event)
            elif post_type == "request":
                self._dispatch_qq_request(plugin, event)
            elif post_type == "message":
                self._dispatch_qq_message(plugin, event)

    def _dispatch_qq_notice(self, plugin: BasePlugin, event: dict[str, Any]) -> None:
        """Dispatch QQ notice event to plugin.

        Args:
            plugin: Plugin instance
            event: Notice event payload
        """
        handler = getattr(plugin, "handle_qq_notice", None)
        if not handler:
            return

        notice_type = event.get("notice_type", "")
        sub_type = event.get("sub_type", "")

        # Handle poke which is under "notify" notice_type
        if notice_type == "notify" and sub_type == "poke":
            notice_type = "poke"

        try:
            handler(notice_type, event)
        except Exception as exc:
            metadata = plugin.metadata()
            logger.error(
                "Plugin '%s' failed to handle QQ notice: %s",
                metadata.name,
                exc,
                exc_info=True,
            )

    def _dispatch_qq_request(self, plugin: BasePlugin, event: dict[str, Any]) -> bool | None:
        """Dispatch QQ request event to plugin.

        Args:
            plugin: Plugin instance
            event: Request event payload

        Returns:
            True to approve, False to reject, None if not handled
        """
        handler = getattr(plugin, "handle_qq_request", None)
        if not handler:
            return None

        request_type = event.get("request_type", "")

        try:
            result = handler(request_type, event)
            return result
        except Exception as exc:
            metadata = plugin.metadata()
            logger.error(
                "Plugin '%s' failed to handle QQ request: %s",
                metadata.name,
                exc,
                exc_info=True,
            )
            return None

    def _dispatch_qq_message(self, plugin: BasePlugin, event: dict[str, Any]) -> str | None:
        """Dispatch QQ message event to plugin.

        Args:
            plugin: Plugin instance
            event: Message event payload

        Returns:
            Response message or None
        """
        handler = getattr(plugin, "handle_qq_message", None)
        if not handler:
            return None

        try:
            result = handler(event)
            if result:
                # Send response back
                message_type = event.get("message_type", "private")
                user_id = event.get("user_id")
                group_id = event.get("group_id")

                if message_type == "group" and group_id:
                    target = f"group:{group_id}"
                elif user_id:
                    target = f"private:{user_id}"
                else:
                    return result

                # Try to send via plugin's QQ provider
                qq_provider = plugin.get_qq_provider()
                if qq_provider:
                    qq_provider.send_text(result, target)
                    logger.debug(
                        "Plugin '%s' sent QQ response to %s",
                        plugin.metadata().name,
                        target,
                    )

            return result
        except Exception as exc:
            metadata = plugin.metadata()
            logger.error(
                "Plugin '%s' failed to handle QQ message: %s",
                metadata.name,
                exc,
                exc_info=True,
            )
            return None

    def dispatch_qq_event(self, event: dict[str, Any]) -> tuple[list[str], bool | None, str | None]:
        """Dispatch QQ event to all plugins and collect results.

        This is a convenience method for handling QQ events that may need
        aggregated responses (e.g., request approval from multiple plugins).

        Args:
            event: QQ event payload

        Returns:
            Tuple of:
            - List of plugin names that handled the event
            - Request approval result (True/False/None for request events)
            - Message response (for message events)
        """
        post_type = event.get("post_type", "")
        handled_by: list[str] = []
        approval_result: bool | None = None
        message_response: str | None = None

        for plugin in self.plugins.values():
            plugin_name = plugin.metadata().name

            if post_type == "notice":
                handler = getattr(plugin, "handle_qq_notice", None)
                if handler:
                    try:
                        notice_type = event.get("notice_type", "")
                        sub_type = event.get("sub_type", "")
                        if notice_type == "notify" and sub_type == "poke":
                            notice_type = "poke"
                        handler(notice_type, event)
                        handled_by.append(plugin_name)
                    except Exception as e:
                        logger.error("Plugin %s notice handler error: %s", plugin_name, e)

            elif post_type == "request":
                result = self._dispatch_qq_request(plugin, event)
                if result is not None:
                    handled_by.append(plugin_name)
                    approval_result = result

            elif post_type == "message":
                result = self._dispatch_qq_message(plugin, event)
                if result is not None:
                    handled_by.append(plugin_name)
                    message_response = result
                    break  # First response wins

        return handled_by, approval_result, message_response

    # =========================================================================
    # Enhanced Plugin Management Methods
    # =========================================================================

    def reload_plugin(self, name: str) -> bool:
        """Reload a specific plugin without affecting others.

        Args:
            name: Plugin name to reload

        Returns:
            True if plugin was reloaded successfully, False otherwise
        """
        if name not in self.plugins:
            logger.warning(f"Plugin not found for reload: {name}")
            return False

        file_path = self._plugin_files.get(name)
        if not file_path or not file_path.exists():
            logger.error(f"Plugin file not found for: {name}")
            return False

        try:
            # Disable and unload existing plugin
            plugin = self.plugins[name]
            was_enabled = self._plugin_enabled.get(name, False)

            try:
                plugin.on_disable()
                plugin.on_unload()
                plugin.cleanup_jobs()
            except Exception as e:
                logger.error(f"Error unloading plugin {name}: {e}")

            # Remove from plugins dict
            del self.plugins[name]

            # Reload from file
            new_plugin = self._load_plugin_from_file(file_path)
            if new_plugin is None:
                logger.error(f"Failed to reload plugin: {name}")
                return False

            # Register and enable if it was enabled before
            new_name = new_plugin.metadata().name
            self.plugins[new_name] = new_plugin
            self._plugin_enabled[new_name] = False
            new_plugin.on_load()

            if was_enabled:
                self.enable_plugin(new_name)

            logger.info(f"Plugin reloaded successfully: {name}")
            return True

        except Exception as e:
            logger.error(f"Error reloading plugin {name}: {e}", exc_info=True)
            return False

    def get_plugin_info(self, name: str) -> PluginInfo | None:
        """Get detailed information about a plugin.

        Args:
            name: Plugin name

        Returns:
            PluginInfo instance or None if plugin not found
        """
        plugin = self.plugins.get(name)
        if not plugin:
            return None

        metadata = plugin.metadata()
        file_path = self._plugin_files.get(name, Path())
        load_time = self._plugin_load_times.get(name, 0.0)

        # Check if plugin has a configuration schema
        has_schema = plugin.config_schema is not None

        # Get permission info
        permissions = [p.name for p in plugin.get_required_permissions()]
        permissions_granted = True
        if self._permission_manager:
            valid, _ = self._permission_manager.validate_plugin_permissions(name)
            permissions_granted = valid

        return PluginInfo(
            name=metadata.name,
            version=metadata.version,
            description=metadata.description,
            author=metadata.author,
            enabled=self._plugin_enabled.get(name, False),
            file_path=str(file_path),
            config=plugin.get_all_config(),
            has_schema=has_schema,
            jobs=list(plugin._job_ids),
            load_time=load_time,
            permissions=permissions,
            permissions_granted=permissions_granted,
        )

    def get_all_plugin_info(self) -> list[PluginInfo]:
        """Get information about all loaded plugins.

        Returns:
            List of PluginInfo instances
        """
        return [self.get_plugin_info(name) for name in self.plugins if self.get_plugin_info(name)]

    def get_plugin_config(self, name: str) -> dict[str, Any]:
        """Get current configuration for a plugin.

        Args:
            name: Plugin name

        Returns:
            Plugin configuration dictionary
        """
        plugin = self.plugins.get(name)
        if not plugin:
            return {}
        return plugin.get_all_config()

    def update_plugin_config(
        self,
        name: str,
        config: dict[str, Any],
        save_to_file: bool = True,
        reload_plugin: bool = False,
    ) -> tuple[bool, list[str]]:
        """Update configuration for a plugin.

        Args:
            name: Plugin name
            config: New configuration values to merge
            save_to_file: Whether to save changes to config file
            reload_plugin: Whether to reload the plugin after config update

        Returns:
            Tuple of (success, list of error messages)
        """
        plugin = self.plugins.get(name)
        if not plugin:
            return False, [f"Plugin not found: {name}"]

        errors: list[str] = []

        # Validate configuration if schema exists
        if plugin.config_schema is not None:
            # Merge with existing config for validation
            existing_config = plugin.get_all_config()
            merged_config = {**existing_config, **config}
            is_valid, validation_errors = plugin.config_schema.validate_config(merged_config)
            if not is_valid:
                return False, validation_errors

        # Save to config file if requested
        if save_to_file:
            try:
                from .config_updater import ConfigUpdater

                config_path = getattr(self.config, "_config_path", None) or "config.yaml"
                updater = ConfigUpdater(config_path)
                updater.update_plugin_settings(name, config, create_backup=True)
                logger.info(f"Saved configuration for plugin: {name}")
            except Exception as e:
                errors.append(f"Failed to save config: {e}")
                logger.error(f"Failed to save plugin config: {e}")

        # Reload plugin if requested
        if reload_plugin and not self.reload_plugin(name):
            errors.append("Failed to reload plugin after config update")

        return len(errors) == 0, errors

    def get_plugin_schema(self, name: str) -> dict[str, Any] | None:
        """Get configuration schema for a plugin.

        Args:
            name: Plugin name

        Returns:
            Schema dictionary or None if no schema defined
        """
        plugin = self.plugins.get(name)
        if not plugin or plugin.config_schema is None:
            return None

        schema_fields = plugin.config_schema.get_schema_fields()
        return {
            field_name: {
                "type": field_def.field_type.value,
                "description": field_def.description,
                "required": field_def.required,
                "default": field_def.default,
                "sensitive": field_def.sensitive,
                "choices": field_def.choices,
                "min_value": field_def.min_value,
                "max_value": field_def.max_value,
            }
            for field_name, field_def in schema_fields.items()
        }

    def is_plugin_enabled(self, name: str) -> bool:
        """Check if a plugin is currently enabled.

        Args:
            name: Plugin name

        Returns:
            True if plugin is enabled, False otherwise
        """
        return self._plugin_enabled.get(name, False)

    def get_available_plugins(self) -> list[dict[str, Any]]:
        """Get list of all available plugins (including disabled ones in config).

        Returns:
            List of plugin info dictionaries
        """
        available = []

        # Get loaded plugins
        for name in self.plugins:
            info = self.get_plugin_info(name)
            if info:
                available.append(info.to_dict())

        # Check for disabled plugins in config
        for plugin_setting in self.config.plugins.plugin_settings:
            if plugin_setting.plugin_name not in self.plugins:
                available.append(
                    {
                        "name": plugin_setting.plugin_name,
                        "version": "unknown",
                        "description": "",
                        "author": "",
                        "enabled": plugin_setting.enabled,
                        "file_path": "",
                        "config": plugin_setting.settings,
                        "has_schema": False,
                        "jobs": [],
                        "load_time": 0.0,
                        "loaded": False,
                    }
                )

        return available

    def set_plugin_enabled_in_config(self, name: str, enabled: bool) -> bool:
        """Set plugin enabled state in configuration file.

        Args:
            name: Plugin name
            enabled: Whether to enable or disable

        Returns:
            True if successful
        """
        try:
            from .config_updater import ConfigUpdater

            config_path = getattr(self.config, "_config_path", None) or "config.yaml"
            updater = ConfigUpdater(config_path)

            # Load current config
            config = updater._load_config()
            updater._ensure_plugins_section(config)

            # Find or create plugin entry
            plugin_entry = updater._find_plugin_entry(config["plugins"]["plugin_settings"], name)

            if plugin_entry is None:
                plugin_entry = {
                    "plugin_name": name,
                    "enabled": enabled,
                    "settings": {},
                }
                config["plugins"]["plugin_settings"].append(plugin_entry)
            else:
                plugin_entry["enabled"] = enabled

            updater._save_config(config)
            logger.info(f"Set plugin {name} enabled={enabled} in config")
            return True

        except Exception as e:
            logger.error(f"Failed to update plugin enabled state: {e}")
            return False

    # ========== Permission Management ==========

    def get_permission_manager(self):
        """Get or create the permission manager.

        Returns:
            PermissionManager instance
        """
        if self._permission_manager is None:
            from .permissions import get_permission_manager

            self._permission_manager = get_permission_manager()
        return self._permission_manager

    def get_sandbox(self):
        """Get or create the sandbox.

        Returns:
            PluginSandbox instance
        """
        if self._sandbox is None:
            from .sandbox import get_sandbox

            self._sandbox = get_sandbox()
        return self._sandbox

    def register_plugin_permissions(self, name: str) -> None:
        """Register a plugin's permissions with the permission manager.

        Args:
            name: Plugin name
        """
        plugin = self.plugins.get(name)
        if not plugin:
            return

        perm_set = plugin.get_permission_set()
        pm = self.get_permission_manager()
        pm.register_plugin_permissions(name, perm_set)

        # Auto-grant non-dangerous permissions
        pm.grant_permissions(name, auto_grant=True)

        logger.debug(
            "Registered permissions for %s: %s",
            name,
            [p.name for p in perm_set.get_all_permissions()],
        )

    def grant_plugin_permission(self, name: str, permission_name: str) -> bool:
        """Grant a specific permission to a plugin.

        Args:
            name: Plugin name
            permission_name: Permission name (e.g., "NETWORK_SEND")

        Returns:
            True if successful
        """
        from .permissions import PluginPermission

        try:
            permission = PluginPermission[permission_name]
            pm = self.get_permission_manager()
            grant = pm.grant_permissions(name, {permission})
            logger.info(f"Granted {permission_name} to plugin {name}")
            return grant is not None
        except KeyError:
            logger.error(f"Unknown permission: {permission_name}")
            return False

    def revoke_plugin_permission(self, name: str, permission_name: str) -> bool:
        """Revoke a specific permission from a plugin.

        Args:
            name: Plugin name
            permission_name: Permission name

        Returns:
            True if successful
        """
        from .permissions import PluginPermission

        try:
            permission = PluginPermission[permission_name]
            pm = self.get_permission_manager()
            pm.revoke_permission(name, permission)
            logger.info(f"Revoked {permission_name} from plugin {name}")
            return True
        except KeyError:
            logger.error(f"Unknown permission: {permission_name}")
            return False

    def get_plugin_permissions(self, name: str) -> dict:
        """Get permission status for a plugin.

        Args:
            name: Plugin name

        Returns:
            Dictionary with permission information
        """
        plugin = self.plugins.get(name)
        if not plugin:
            return {}

        pm = self.get_permission_manager()
        grant = pm.get_grant(name)

        required = plugin.get_required_permissions()
        granted = grant.granted if grant else set()
        denied = grant.denied if grant else set()
        pending_dangerous = pm.get_pending_dangerous_approvals(name)

        return {
            "required": [p.name for p in required],
            "granted": [p.name for p in granted],
            "denied": [p.name for p in denied],
            "pending_dangerous": [p.name for p in pending_dangerous],
            "all_granted": len(required - granted) == 0,
        }

    def approve_dangerous_permission(self, name: str, permission_name: str) -> bool:
        """Approve a dangerous permission for a plugin.

        Args:
            name: Plugin name
            permission_name: Permission name

        Returns:
            True if successful
        """
        from .permissions import DANGEROUS_PERMISSIONS, PluginPermission

        try:
            permission = PluginPermission[permission_name]
            if permission not in DANGEROUS_PERMISSIONS:
                logger.warning(f"{permission_name} is not a dangerous permission")
                return False

            pm = self.get_permission_manager()
            grant = pm.get_grant(name) or pm.grant_permissions(name)
            grant.approve_dangerous(permission)
            logger.info(f"Approved dangerous permission {permission_name} for {name}")
            return True
        except KeyError:
            logger.error(f"Unknown permission: {permission_name}")
            return False

    def get_sandbox_violations(self, name: str | None = None) -> list[dict]:
        """Get sandbox violations for a plugin.

        Args:
            name: Plugin name (None = all)

        Returns:
            List of violation dictionaries
        """
        sandbox = self.get_sandbox()
        violations = sandbox.get_violations(name)
        return [v.to_dict() for v in violations]
