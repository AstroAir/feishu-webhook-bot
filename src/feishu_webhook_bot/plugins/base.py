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

    # ========== QQ/OneBot11 Support ==========

    def get_qq_provider(self) -> BaseProvider | None:
        """Get QQ/Napcat provider for QQ-specific operations.

        Returns:
            QQ provider instance or None if not available
        """
        return self._providers.get("napcat") or self._providers.get("qq")

    def handle_qq_notice(self, notice_type: str, event: dict[str, Any]) -> None:
        """Handle QQ notice events.

        Override this method to handle QQ notice events such as:
        - group_increase: New member joined group
        - group_decrease: Member left/kicked from group
        - group_ban: Member banned/unbanned
        - friend_add: New friend added
        - poke (notify): Poke notification

        Args:
            notice_type: Notice type (group_increase, group_decrease, etc.)
            event: Full event payload with fields like group_id, user_id, etc.

        Example:
            ```python
            def handle_qq_notice(self, notice_type: str, event: dict) -> None:
                if notice_type == "group_increase":
                    group_id = event.get("group_id")
                    user_id = event.get("user_id")
                    self.send_qq_message(f"欢迎 [CQ:at,qq={user_id}]！", f"group:{group_id}")
            ```
        """
        pass

    def handle_qq_request(self, request_type: str, event: dict[str, Any]) -> bool | None:
        """Handle QQ request events.

        Override this method to handle QQ request events such as:
        - friend: Friend add request
        - group: Group add/invite request

        Args:
            request_type: Request type (friend, group)
            event: Full event payload with fields like user_id, flag, comment, etc.

        Returns:
            True to approve, False to reject, None to ignore (let other handlers decide)

        Example:
            ```python
            def handle_qq_request(self, request_type: str, event: dict) -> bool | None:
                if request_type == "friend":
                    # Auto-approve friends with keyword in comment
                    if "验证码123" in event.get("comment", ""):
                        return True
                return None  # Let other handlers decide
            ```
        """
        return None

    def handle_qq_message(self, message: dict[str, Any]) -> str | None:
        """Handle QQ message events.

        Override this method to handle QQ messages. This is called before AI processing
        and can be used for command handling or keyword responses.

        Args:
            message: Message event payload with fields like:
                - message_type: "private" or "group"
                - user_id: Sender QQ number
                - group_id: Group ID (for group messages)
                - raw_message: Raw message content
                - message: Message segments array

        Returns:
            Response message to send back, or None to not respond

        Example:
            ```python
            def handle_qq_message(self, message: dict) -> str | None:
                content = message.get("raw_message", "")
                if content == "/ping":
                    return "pong!"
                return None
            ```
        """
        return None

    def send_qq_message(self, content: str, target: str) -> bool:
        """Send a message via QQ provider.

        Args:
            content: Message content (supports CQ codes)
            target: Target in format "group:123456" or "private:123456"

        Returns:
            True if sent successfully, False otherwise

        Example:
            ```python
            # Send to group
            self.send_qq_message("Hello group!", "group:123456789")

            # Send to private
            self.send_qq_message("Hello!", "private:987654321")

            # Send with @mention
            self.send_qq_message("[CQ:at,qq=123] Hello!", "group:456")
            ```
        """
        provider = self.get_qq_provider()
        if not provider:
            self.logger.warning("QQ provider not available")
            return False

        try:
            provider.send_text(content, target)
            return True
        except Exception as e:
            self.logger.error("Failed to send QQ message: %s", e)
            return False

    def send_qq_poke(self, user_id: int, group_id: int | None = None) -> bool:
        """Send a poke via QQ provider.

        Args:
            user_id: Target user QQ number
            group_id: Group ID for group poke, None for private poke

        Returns:
            True if sent successfully, False otherwise
        """
        provider = self.get_qq_provider()
        if not provider or not hasattr(provider, "send_poke"):
            self.logger.warning("QQ poke not available")
            return False

        try:
            provider.send_poke(user_id, group_id)
            return True
        except Exception as e:
            self.logger.error("Failed to send poke: %s", e)
            return False

    def send_qq_image(self, image_url: str, target: str) -> bool:
        """Send an image via QQ provider.

        Args:
            image_url: Image URL or local file path
            target: Target in format "group:123456" or "private:123456"

        Returns:
            True if sent successfully, False otherwise
        """
        provider = self.get_qq_provider()
        if not provider or not hasattr(provider, "send_image"):
            self.logger.warning("QQ image sending not available")
            return False

        try:
            provider.send_image(image_url, target)
            return True
        except Exception as e:
            self.logger.error("Failed to send QQ image: %s", e)
            return False

    def qq_set_group_ban(self, group_id: int, user_id: int, duration: int = 1800) -> bool:
        """Mute a user in a group.

        Args:
            group_id: Group ID
            user_id: User to mute
            duration: Mute duration in seconds (0 to unmute)

        Returns:
            True if successful
        """
        provider = self.get_qq_provider()
        if not provider or not hasattr(provider, "set_group_ban"):
            return False

        try:
            provider.set_group_ban(group_id, user_id, duration)
            return True
        except Exception as e:
            self.logger.error("Failed to set group ban: %s", e)
            return False

    def qq_set_group_kick(self, group_id: int, user_id: int, reject_add: bool = False) -> bool:
        """Kick a user from a group.

        Args:
            group_id: Group ID
            user_id: User to kick
            reject_add: Whether to reject future join requests

        Returns:
            True if successful
        """
        provider = self.get_qq_provider()
        if not provider or not hasattr(provider, "set_group_kick"):
            return False

        try:
            provider.set_group_kick(group_id, user_id, reject_add)
            return True
        except Exception as e:
            self.logger.error("Failed to kick user: %s", e)
            return False

    def qq_approve_friend_request(self, flag: str, approve: bool = True) -> bool:
        """Approve or reject a friend request.

        Args:
            flag: Request flag from the request event
            approve: True to approve, False to reject

        Returns:
            True if successful
        """
        provider = self.get_qq_provider()
        if not provider or not hasattr(provider, "set_friend_add_request"):
            return False

        try:
            provider.set_friend_add_request(flag, approve=approve)
            return True
        except Exception as e:
            self.logger.error("Failed to handle friend request: %s", e)
            return False

    def qq_approve_group_request(self, flag: str, sub_type: str, approve: bool = True) -> bool:
        """Approve or reject a group join/invite request.

        Args:
            flag: Request flag from the request event
            sub_type: "add" for join request, "invite" for invite
            approve: True to approve, False to reject

        Returns:
            True if successful
        """
        provider = self.get_qq_provider()
        if not provider or not hasattr(provider, "set_group_add_request"):
            return False

        try:
            provider.set_group_add_request(flag, sub_type=sub_type, approve=approve)
            return True
        except Exception as e:
            self.logger.error("Failed to handle group request: %s", e)
            return False

    def qq_get_group_list(self) -> list[dict[str, Any]]:
        """Get list of groups the bot is in.

        Returns:
            List of group info dicts with group_id, group_name, etc.
        """
        provider = self.get_qq_provider()
        if not provider or not hasattr(provider, "get_group_list"):
            return []

        try:
            return provider.get_group_list() or []
        except Exception as e:
            self.logger.error("Failed to get group list: %s", e)
            return []

    def qq_get_group_member_list(self, group_id: int) -> list[dict[str, Any]]:
        """Get list of members in a group.

        Args:
            group_id: Group ID

        Returns:
            List of member info dicts
        """
        provider = self.get_qq_provider()
        if not provider or not hasattr(provider, "get_group_member_list"):
            return []

        try:
            return provider.get_group_member_list(group_id) or []
        except Exception as e:
            self.logger.error("Failed to get group member list: %s", e)
            return []

    # ========== Configuration Schema Support (Optional) ==========

    # Optional class attributes for advanced features
    # Subclasses can set these to enable configuration schema and manifest support
    config_schema: type[PluginConfigSchema] | None = None
    PYTHON_DEPENDENCIES: list = []
    PLUGIN_DEPENDENCIES: list = []
    PERMISSIONS: list = []  # List of PluginPermission enums

    def get_required_permissions(self) -> set:
        """Get the permissions required by this plugin.

        Returns:
            Set of PluginPermission enums
        """
        from .permissions import PluginPermission

        perms = set()
        for p in self.PERMISSIONS:
            if isinstance(p, PluginPermission):
                perms.add(p)
            elif isinstance(p, str):
                try:
                    perms.add(PluginPermission[p])
                except KeyError:
                    self.logger.warning("Unknown permission: %s", p)
        return perms

    def get_permission_set(self):
        """Get the full permission set for this plugin.

        Returns:
            PluginPermissionSet instance
        """
        from .permissions import PluginPermissionSet

        return PluginPermissionSet(required=self.get_required_permissions())

    def check_permission(self, permission) -> bool:
        """Check if this plugin has a specific permission.

        Args:
            permission: PluginPermission to check

        Returns:
            True if permission is granted
        """
        from .permissions import get_permission_manager

        return get_permission_manager().check_permission(self.metadata().name, permission)

    def require_permission(self, permission) -> None:
        """Require a permission, raising an error if not granted.

        Args:
            permission: PluginPermission required

        Raises:
            PermissionError: If permission is not granted
        """
        from .permissions import get_permission_manager

        get_permission_manager().require_permission(self.metadata().name, permission)

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
