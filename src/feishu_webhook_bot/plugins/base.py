"""Base plugin class and metadata.

All plugins should inherit from BasePlugin and implement the required methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..core.config import BotConfig
from ..core.logger import get_logger

if TYPE_CHECKING:
    from ..core.client import FeishuWebhookClient
    from ..core.provider import BaseProvider
    from .config_schema import PluginConfigSchema
    from .manifest import PluginManifest


@dataclass
class PluginMetadata:
    """Metadata for a plugin.

    Attributes:
        name: Plugin name
        version: Plugin version
        description: Plugin description
        author: Plugin author
        enabled: Whether plugin is enabled
    """

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    enabled: bool = True


class BasePlugin(ABC):
    """Base class for all plugins.

    All plugins must inherit from this class and implement the required methods.

    The plugin system supports both the legacy FeishuWebhookClient and the new
    multi-provider architecture. Plugins can access:
    - self.client: The default provider/client (backward compatible)
    - self.providers: Dict of all available providers (new)
    - self.get_provider(name): Get a specific provider by name

    Example:
        ```python
        from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

        class MyPlugin(BasePlugin):
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my-plugin",
                    version="1.0.0",
                    description="My custom plugin"
                )

            def on_load(self) -> None:
                self.logger.info("Plugin loaded")

            def on_enable(self) -> None:
                # Register scheduled jobs
                self.register_job(self.my_task, trigger='interval', minutes=5)

            def my_task(self):
                # Use default client (backward compatible)
                self.client.send_text("Hello from plugin!")

                # Or use specific provider
                qq_provider = self.get_provider("qq")
                if qq_provider:
                    qq_provider.send_text("Hello QQ!", "group:123456")
        ```
    """

    def __init__(
        self,
        config: BotConfig,
        client: FeishuWebhookClient | BaseProvider | None = None,
        providers: dict[str, BaseProvider] | None = None,
    ):
        """Initialize the plugin.

        Args:
            config: Bot configuration
            client: Default webhook client or provider (for backward compatibility)
            providers: Dict of all available providers (new multi-provider support)
        """
        self.config = config
        self._client = client
        self._providers: dict[str, BaseProvider] = providers or {}
        self.logger = get_logger(f"plugin.{self.metadata().name}")
        self._job_ids: list[str] = []

    @property
    def client(self) -> FeishuWebhookClient | BaseProvider | None:
        """Get the default client/provider for backward compatibility."""
        return self._client

    @client.setter
    def client(self, value: FeishuWebhookClient | BaseProvider | None) -> None:
        """Set the default client/provider."""
        self._client = value

    @property
    def providers(self) -> dict[str, BaseProvider]:
        """Get all available providers."""
        return self._providers

    @providers.setter
    def providers(self, value: dict[str, BaseProvider]) -> None:
        """Set the providers dict."""
        self._providers = value

    def get_provider(self, name: str) -> BaseProvider | None:
        """Get a specific provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(name)

    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata.

        Returns:
            PluginMetadata instance
        """
        pass

    def on_load(self) -> None:
        """Called when plugin is loaded.

        This is called during plugin discovery and loading.
        Use this for initialization that doesn't require the bot to be running.
        """
        self.logger.debug("on_load called for %s", self.__class__.__name__)

    def on_enable(self) -> None:
        """Called when plugin is enabled.

        This is called after the bot starts and the plugin is ready to use.
        Use this to register scheduled jobs, set up resources, etc.
        """
        self.logger.debug("on_enable default no-op for %s", self.__class__.__name__)

    def on_disable(self) -> None:
        """Called when plugin is disabled or bot is shutting down.

        Use this to clean up resources, save state, etc.
        """
        self.logger.debug("on_disable default no-op for %s", self.__class__.__name__)

    def on_unload(self) -> None:
        """Called when plugin is unloaded (before hot reload).

        Use this for cleanup before the plugin is reloaded.
        """
        self.logger.debug("on_unload default no-op for %s", self.__class__.__name__)

    def register_job(
        self,
        func: Any,
        trigger: str = "interval",
        job_id: str | None = None,
        **trigger_args: Any,
    ) -> str:
        """Register a scheduled job for this plugin.

        The job will be automatically removed when the plugin is disabled.

        Args:
            func: Function to execute
            trigger: Trigger type ('interval', 'cron')
            job_id: Optional job ID
            **trigger_args: Trigger-specific arguments

        Returns:
            Job ID
        """
        # This will be implemented by the plugin manager
        # For now, we just store the job_id for cleanup
        if job_id:
            self._job_ids.append(job_id)
        return job_id or ""

    def cleanup_jobs(self) -> None:
        """Clean up all registered jobs.

        This is called automatically when the plugin is disabled.
        """
        self._job_ids.clear()

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from plugin-specific settings.

        This is a helper to access configuration values defined in the YAML
        configuration file under plugins.plugin_settings for this plugin.

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default

        Example:
            In config.yaml:
            ```yaml
            plugins:
              plugin_settings:
                - plugin_name: "my-plugin"
                  settings:
                    api_key: "secret123"
                    threshold: 80
            ```

            In plugin code:
            ```python
            api_key = self.get_config_value("api_key", "default_key")
            threshold = self.get_config_value("threshold", 50)
            ```
        """
        plugin_name = self.metadata().name
        plugin_settings = self.config.plugins.get_plugin_settings(plugin_name)
        return plugin_settings.get(key, default)

    def get_all_config(self) -> dict[str, Any]:
        """Get all configuration values for this plugin.

        Returns:
            Dictionary of all plugin-specific configuration values
        """
        plugin_name = self.metadata().name
        return self.config.plugins.get_plugin_settings(plugin_name)

    def handle_event(self, event: dict[str, Any], context: dict[str, Any] | None = None) -> None:
        """Handle an inbound Feishu event.

        Plugins can override this to implement reactive behaviour triggered by
        webhook events forwarded by the bot. The default implementation is a
        no-op.
        """
        return None

    # ========== Configuration Schema Support (Optional) ==========

    # Optional class attributes for enhanced features
    # Subclasses can set these to enable configuration schema and manifest support
    config_schema: type[PluginConfigSchema] | None = None
    PYTHON_DEPENDENCIES: list = []
    PLUGIN_DEPENDENCIES: list = []
    PERMISSIONS: list = []

    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate this plugin's configuration against its schema.

        Returns:
            Tuple of (is_valid, list_of_error_messages)

        Default implementation returns (True, []) for backward compatibility
        if no schema is defined.
        """
        if self.config_schema is None:
            return True, []

        existing_config = self.get_all_config()
        return self.config_schema.validate_config(existing_config)

    def get_missing_config(self) -> list[str]:
        """Get list of missing required configuration fields.

        Returns:
            List of field names that are required but not configured.
            Empty list if no schema is defined.
        """
        if self.config_schema is None:
            return []

        existing_config = self.get_all_config()
        missing = self.config_schema.get_missing_required(existing_config)
        return [f.name for f in missing]

    def get_manifest(self) -> PluginManifest:
        """Return the plugin manifest with dependencies and permissions.

        Override this method to provide complete manifest information.
        Default implementation creates manifest from class attributes.

        Returns:
            PluginManifest instance
        """
        from .manifest import PluginManifest

        return PluginManifest.from_plugin(self)
