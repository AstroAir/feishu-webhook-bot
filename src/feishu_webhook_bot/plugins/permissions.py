"""Plugin permission system.

This module provides a permission system for plugins to declare and enforce
access control for various capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from ..core.logger import get_logger

logger = get_logger("plugin_permissions")


class PluginPermission(Enum):
    """Available permissions for plugins.

    Plugins must declare which permissions they need. The system will
    verify these permissions before allowing certain operations.
    """

    # Network permissions
    NETWORK_SEND = auto()  # Send messages via webhook/provider
    NETWORK_HTTP = auto()  # Make HTTP requests to external services
    NETWORK_WEBSOCKET = auto()  # Use WebSocket connections

    # File system permissions
    FILE_READ = auto()  # Read files from disk
    FILE_WRITE = auto()  # Write files to disk
    FILE_PLUGIN_DIR = auto()  # Access plugin directory only

    # System permissions
    SYSTEM_INFO = auto()  # Access system information (CPU, memory, etc.)
    SYSTEM_EXEC = auto()  # Execute system commands (dangerous!)
    SYSTEM_ENV = auto()  # Access environment variables

    # Scheduler permissions
    SCHEDULER_JOBS = auto()  # Register scheduled jobs
    SCHEDULER_MANAGE = auto()  # Manage other jobs (pause, remove)

    # Configuration permissions
    CONFIG_READ = auto()  # Read bot configuration
    CONFIG_WRITE = auto()  # Modify bot configuration

    # Database permissions
    DATABASE_READ = auto()  # Read from database
    DATABASE_WRITE = auto()  # Write to database

    # AI permissions
    AI_CHAT = auto()  # Use AI chat capabilities
    AI_TOOLS = auto()  # Register AI tools

    # Event permissions
    EVENT_LISTEN = auto()  # Listen to bot events
    EVENT_EMIT = auto()  # Emit custom events

    # Provider permissions
    PROVIDER_ACCESS = auto()  # Access message providers
    PROVIDER_MANAGE = auto()  # Manage provider connections


class PermissionLevel(Enum):
    """Permission levels for quick permission sets."""

    MINIMAL = auto()  # Only basic messaging
    STANDARD = auto()  # Common plugin needs
    ELEVATED = auto()  # Extended capabilities
    FULL = auto()  # All permissions (dangerous)


# Predefined permission sets for each level
PERMISSION_LEVELS: dict[PermissionLevel, set[PluginPermission]] = {
    PermissionLevel.MINIMAL: {
        PluginPermission.NETWORK_SEND,
        PluginPermission.CONFIG_READ,
    },
    PermissionLevel.STANDARD: {
        PluginPermission.NETWORK_SEND,
        PluginPermission.NETWORK_HTTP,
        PluginPermission.FILE_PLUGIN_DIR,
        PluginPermission.SCHEDULER_JOBS,
        PluginPermission.CONFIG_READ,
        PluginPermission.EVENT_LISTEN,
        PluginPermission.PROVIDER_ACCESS,
    },
    PermissionLevel.ELEVATED: {
        PluginPermission.NETWORK_SEND,
        PluginPermission.NETWORK_HTTP,
        PluginPermission.NETWORK_WEBSOCKET,
        PluginPermission.FILE_READ,
        PluginPermission.FILE_WRITE,
        PluginPermission.FILE_PLUGIN_DIR,
        PluginPermission.SYSTEM_INFO,
        PluginPermission.SCHEDULER_JOBS,
        PluginPermission.SCHEDULER_MANAGE,
        PluginPermission.CONFIG_READ,
        PluginPermission.CONFIG_WRITE,
        PluginPermission.DATABASE_READ,
        PluginPermission.DATABASE_WRITE,
        PluginPermission.AI_CHAT,
        PluginPermission.AI_TOOLS,
        PluginPermission.EVENT_LISTEN,
        PluginPermission.EVENT_EMIT,
        PluginPermission.PROVIDER_ACCESS,
    },
    PermissionLevel.FULL: set(PluginPermission),
}

# Dangerous permissions that require explicit approval
DANGEROUS_PERMISSIONS: set[PluginPermission] = {
    PluginPermission.SYSTEM_EXEC,
    PluginPermission.SYSTEM_ENV,
    PluginPermission.CONFIG_WRITE,
    PluginPermission.FILE_WRITE,
    PluginPermission.PROVIDER_MANAGE,
}


@dataclass
class PluginPermissionSet:
    """A set of permissions for a plugin.

    Attributes:
        required: Permissions the plugin requires to function
        optional: Permissions the plugin can use if granted
        level: Permission level (alternative to explicit permissions)
    """

    required: set[PluginPermission] = field(default_factory=set)
    optional: set[PluginPermission] = field(default_factory=set)
    level: PermissionLevel | None = None

    def get_all_permissions(self) -> set[PluginPermission]:
        """Get all permissions (required + optional + level)."""
        perms = self.required | self.optional
        if self.level:
            perms |= PERMISSION_LEVELS.get(self.level, set())
        return perms

    def get_required_permissions(self) -> set[PluginPermission]:
        """Get required permissions including level defaults."""
        perms = self.required.copy()
        if self.level:
            perms |= PERMISSION_LEVELS.get(self.level, set())
        return perms

    def has_dangerous_permissions(self) -> bool:
        """Check if any dangerous permissions are requested."""
        return bool(self.get_all_permissions() & DANGEROUS_PERMISSIONS)

    def get_dangerous_permissions(self) -> set[PluginPermission]:
        """Get the dangerous permissions requested."""
        return self.get_all_permissions() & DANGEROUS_PERMISSIONS

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "required": [p.name for p in self.required],
            "optional": [p.name for p in self.optional],
            "level": self.level.name if self.level else None,
            "all_permissions": [p.name for p in self.get_all_permissions()],
            "has_dangerous": self.has_dangerous_permissions(),
            "dangerous_permissions": [p.name for p in self.get_dangerous_permissions()],
        }


@dataclass
class PluginPermissionGrant:
    """Granted permissions for a plugin.

    Attributes:
        plugin_name: Name of the plugin
        granted: Set of granted permissions
        denied: Set of explicitly denied permissions
        approved_dangerous: Dangerous permissions that were approved
    """

    plugin_name: str
    granted: set[PluginPermission] = field(default_factory=set)
    denied: set[PluginPermission] = field(default_factory=set)
    approved_dangerous: set[PluginPermission] = field(default_factory=set)

    def is_granted(self, permission: PluginPermission) -> bool:
        """Check if a permission is granted."""
        if permission in self.denied:
            return False
        return permission in self.granted

    def grant(self, permission: PluginPermission) -> None:
        """Grant a permission."""
        self.granted.add(permission)
        self.denied.discard(permission)

    def deny(self, permission: PluginPermission) -> None:
        """Deny a permission."""
        self.denied.add(permission)
        self.granted.discard(permission)

    def approve_dangerous(self, permission: PluginPermission) -> None:
        """Approve a dangerous permission."""
        if permission in DANGEROUS_PERMISSIONS:
            self.approved_dangerous.add(permission)
            self.grant(permission)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plugin_name": self.plugin_name,
            "granted": [p.name for p in self.granted],
            "denied": [p.name for p in self.denied],
            "approved_dangerous": [p.name for p in self.approved_dangerous],
        }


class PermissionManager:
    """Manages plugin permissions.

    This class handles permission checking, granting, and enforcement.
    """

    def __init__(self) -> None:
        """Initialize the permission manager."""
        self._grants: dict[str, PluginPermissionGrant] = {}
        self._plugin_permissions: dict[str, PluginPermissionSet] = {}

    def register_plugin_permissions(
        self, plugin_name: str, permissions: PluginPermissionSet
    ) -> None:
        """Register a plugin's permission requirements.

        Args:
            plugin_name: Name of the plugin
            permissions: Permission set for the plugin
        """
        self._plugin_permissions[plugin_name] = permissions
        logger.debug("Registered permissions for plugin: %s", plugin_name)

    def get_plugin_permissions(self, plugin_name: str) -> PluginPermissionSet | None:
        """Get a plugin's permission requirements."""
        return self._plugin_permissions.get(plugin_name)

    def grant_permissions(
        self,
        plugin_name: str,
        permissions: set[PluginPermission] | None = None,
        auto_grant: bool = True,
    ) -> PluginPermissionGrant:
        """Grant permissions to a plugin.

        Args:
            plugin_name: Name of the plugin
            permissions: Specific permissions to grant (None = auto based on requirements)
            auto_grant: If True, auto-grant non-dangerous required permissions

        Returns:
            PluginPermissionGrant instance
        """
        if plugin_name not in self._grants:
            self._grants[plugin_name] = PluginPermissionGrant(plugin_name=plugin_name)

        grant = self._grants[plugin_name]

        if permissions:
            for perm in permissions:
                if perm in DANGEROUS_PERMISSIONS:
                    grant.approve_dangerous(perm)
                else:
                    grant.grant(perm)
        elif auto_grant:
            # Auto-grant non-dangerous required permissions
            plugin_perms = self._plugin_permissions.get(plugin_name)
            if plugin_perms:
                for perm in plugin_perms.get_required_permissions():
                    if perm not in DANGEROUS_PERMISSIONS:
                        grant.grant(perm)

        return grant

    def get_grant(self, plugin_name: str) -> PluginPermissionGrant | None:
        """Get the permission grant for a plugin."""
        return self._grants.get(plugin_name)

    def check_permission(self, plugin_name: str, permission: PluginPermission) -> bool:
        """Check if a plugin has a specific permission.

        Args:
            plugin_name: Name of the plugin
            permission: Permission to check

        Returns:
            True if permission is granted
        """
        grant = self._grants.get(plugin_name)
        if not grant:
            return False
        return grant.is_granted(permission)

    def require_permission(self, plugin_name: str, permission: PluginPermission) -> None:
        """Require a permission, raising an error if not granted.

        Args:
            plugin_name: Name of the plugin
            permission: Required permission

        Raises:
            PermissionError: If permission is not granted
        """
        if not self.check_permission(plugin_name, permission):
            raise PermissionError(
                f"Plugin '{plugin_name}' does not have permission: {permission.name}"
            )

    def validate_plugin_permissions(self, plugin_name: str) -> tuple[bool, list[str]]:
        """Validate that a plugin has all required permissions.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Tuple of (is_valid, list of missing permissions)
        """
        plugin_perms = self._plugin_permissions.get(plugin_name)
        if not plugin_perms:
            return True, []

        grant = self._grants.get(plugin_name)
        if not grant:
            missing = [p.name for p in plugin_perms.get_required_permissions()]
            return False, missing

        missing = []
        for perm in plugin_perms.get_required_permissions():
            if not grant.is_granted(perm):
                missing.append(perm.name)

        return len(missing) == 0, missing

    def get_pending_dangerous_approvals(self, plugin_name: str) -> set[PluginPermission]:
        """Get dangerous permissions that need approval.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Set of dangerous permissions needing approval
        """
        plugin_perms = self._plugin_permissions.get(plugin_name)
        if not plugin_perms:
            return set()

        grant = self._grants.get(plugin_name)
        dangerous = plugin_perms.get_dangerous_permissions()

        if not grant:
            return dangerous

        return dangerous - grant.approved_dangerous

    def revoke_permission(self, plugin_name: str, permission: PluginPermission) -> None:
        """Revoke a permission from a plugin.

        Args:
            plugin_name: Name of the plugin
            permission: Permission to revoke
        """
        grant = self._grants.get(plugin_name)
        if grant:
            grant.deny(permission)
            grant.approved_dangerous.discard(permission)

    def revoke_all(self, plugin_name: str) -> None:
        """Revoke all permissions from a plugin.

        Args:
            plugin_name: Name of the plugin
        """
        if plugin_name in self._grants:
            del self._grants[plugin_name]

    def get_all_grants(self) -> dict[str, PluginPermissionGrant]:
        """Get all permission grants."""
        return self._grants.copy()

    def clear(self) -> None:
        """Clear all permissions and grants."""
        self._grants.clear()
        self._plugin_permissions.clear()


# Global permission manager instance
_permission_manager: PermissionManager | None = None


def get_permission_manager() -> PermissionManager:
    """Get the global permission manager instance."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


def require_permission(permission: PluginPermission):
    """Decorator to require a permission for a method.

    Usage:
        @require_permission(PluginPermission.NETWORK_SEND)
        def send_message(self, text: str):
            ...
    """

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            plugin_name = self.metadata().name if hasattr(self, "metadata") else "unknown"
            manager = get_permission_manager()
            manager.require_permission(plugin_name, permission)
            return func(self, *args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
