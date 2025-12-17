"""Plugin system for extensible bot functionality.

This package provides:
- Base plugin class
- Plugin manager with discovery and loading
- Hot-reload support via file watching
- Plugin configuration schema support
- Permission system for access control
- Sandbox execution environment
- QQ/OneBot11 integration support
"""

from .base import BasePlugin, PluginMetadata
from .manager import PluginInfo, PluginManager
from .permissions import (
    DANGEROUS_PERMISSIONS,
    PERMISSION_LEVELS,
    PermissionLevel,
    PermissionManager,
    PluginPermission,
    PluginPermissionGrant,
    PluginPermissionSet,
    get_permission_manager,
    require_permission,
)
from .qq_mixin import (
    QQMessageEvent,
    QQMessageType,
    QQNoticeEvent,
    QQNoticeType,
    QQPluginMixin,
    QQRequestEvent,
    QQRequestType,
    on_qq_message,
    on_qq_notice,
    on_qq_poke,
    on_qq_request,
)
from .sandbox import (
    PluginContext,
    PluginSandbox,
    SandboxConfig,
    SandboxViolation,
    configure_sandbox,
    get_sandbox,
)

__all__ = [
    # Base
    "BasePlugin",
    "PluginMetadata",
    # Manager
    "PluginInfo",
    "PluginManager",
    # Permissions
    "PluginPermission",
    "PermissionLevel",
    "PluginPermissionSet",
    "PluginPermissionGrant",
    "PermissionManager",
    "PERMISSION_LEVELS",
    "DANGEROUS_PERMISSIONS",
    "get_permission_manager",
    "require_permission",
    # Sandbox
    "SandboxConfig",
    "SandboxViolation",
    "PluginSandbox",
    "PluginContext",
    "get_sandbox",
    "configure_sandbox",
    # QQ/OneBot11 Support
    "QQPluginMixin",
    "QQNoticeType",
    "QQRequestType",
    "QQMessageType",
    "QQNoticeEvent",
    "QQRequestEvent",
    "QQMessageEvent",
    "on_qq_notice",
    "on_qq_poke",
    "on_qq_request",
    "on_qq_message",
]
