"""Base plugin class and metadata.

All plugins should inherit from BasePlugin and implement the required methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..core.client import FeishuWebhookClient
from ..core.config import BotConfig
from ..core.logger import get_logger


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
                self.client.send_text("Hello from plugin!")
        ```
    """

    def __init__(self, config: BotConfig, client: FeishuWebhookClient):
        """Initialize the plugin.

        Args:
            config: Bot configuration
            client: Feishu webhook client
        """
        self.config = config
        self.client = client
        self.logger = get_logger(f"plugin.{self.metadata().name}")
        self._job_ids: list[str] = []

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
        """Get a configuration value.

        This is a helper to access configuration values.

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        # Plugins can store config in config file under plugins section
        return default

    def handle_event(self, event: dict[str, Any], context: dict[str, Any] | None = None) -> None:
        """Handle an inbound Feishu event.

        Plugins can override this to implement reactive behaviour triggered by
        webhook events forwarded by the bot. The default implementation is a
        no-op.
        """
        return None
