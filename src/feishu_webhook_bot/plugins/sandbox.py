"""Plugin sandbox execution environment.

This module provides a sandboxed execution environment for plugins,
restricting access to dangerous operations based on permissions.
"""

from __future__ import annotations

import functools
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.logger import get_logger
from .permissions import (
    PermissionManager,
    PluginPermission,
    get_permission_manager,
)

logger = get_logger("plugin_sandbox")


@dataclass
class SandboxConfig:
    """Configuration for the plugin sandbox.

    Attributes:
        enabled: Whether sandbox is enabled
        max_execution_time: Maximum execution time per call (seconds)
        max_memory_mb: Maximum memory usage (MB, 0 = unlimited)
        allowed_paths: List of allowed file paths
        blocked_modules: List of blocked module names
        network_whitelist: List of allowed network hosts
    """

    enabled: bool = True
    max_execution_time: float = 30.0
    max_memory_mb: int = 0
    allowed_paths: list[str] = field(default_factory=list)
    blocked_modules: list[str] = field(
        default_factory=lambda: [
            "subprocess",
            "os.system",
            "ctypes",
            "multiprocessing",
        ]
    )
    network_whitelist: list[str] = field(default_factory=list)


@dataclass
class SandboxViolation:
    """Record of a sandbox violation.

    Attributes:
        plugin_name: Name of the plugin
        violation_type: Type of violation
        details: Additional details
        timestamp: When the violation occurred
    """

    plugin_name: str
    violation_type: str
    details: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plugin_name": self.plugin_name,
            "violation_type": self.violation_type,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class PluginSandbox:
    """Sandbox environment for plugin execution.

    This class provides a controlled execution environment for plugins,
    enforcing permissions and resource limits.
    """

    def __init__(
        self,
        config: SandboxConfig | None = None,
        permission_manager: PermissionManager | None = None,
    ) -> None:
        """Initialize the sandbox.

        Args:
            config: Sandbox configuration
            permission_manager: Permission manager instance
        """
        self.config = config or SandboxConfig()
        self.permission_manager = permission_manager or get_permission_manager()
        self._violations: list[SandboxViolation] = []
        self._plugin_contexts: dict[str, PluginContext] = {}
        self._lock = threading.Lock()

    def create_context(self, plugin_name: str) -> PluginContext:
        """Create an execution context for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginContext instance
        """
        with self._lock:
            if plugin_name not in self._plugin_contexts:
                self._plugin_contexts[plugin_name] = PluginContext(
                    plugin_name=plugin_name,
                    sandbox=self,
                )
            return self._plugin_contexts[plugin_name]

    def get_context(self, plugin_name: str) -> PluginContext | None:
        """Get the execution context for a plugin."""
        return self._plugin_contexts.get(plugin_name)

    def remove_context(self, plugin_name: str) -> None:
        """Remove the execution context for a plugin."""
        with self._lock:
            self._plugin_contexts.pop(plugin_name, None)

    def record_violation(
        self,
        plugin_name: str,
        violation_type: str,
        details: str,
    ) -> None:
        """Record a sandbox violation.

        Args:
            plugin_name: Name of the plugin
            violation_type: Type of violation
            details: Additional details
        """
        violation = SandboxViolation(
            plugin_name=plugin_name,
            violation_type=violation_type,
            details=details,
        )
        with self._lock:
            self._violations.append(violation)
        logger.warning(
            "Sandbox violation by '%s': %s - %s",
            plugin_name,
            violation_type,
            details,
        )

    def get_violations(self, plugin_name: str | None = None) -> list[SandboxViolation]:
        """Get recorded violations.

        Args:
            plugin_name: Filter by plugin name (None = all)

        Returns:
            List of violations
        """
        with self._lock:
            if plugin_name:
                return [v for v in self._violations if v.plugin_name == plugin_name]
            return self._violations.copy()

    def clear_violations(self, plugin_name: str | None = None) -> None:
        """Clear recorded violations.

        Args:
            plugin_name: Clear only for this plugin (None = all)
        """
        with self._lock:
            if plugin_name:
                self._violations = [v for v in self._violations if v.plugin_name != plugin_name]
            else:
                self._violations.clear()

    def check_file_access(self, plugin_name: str, path: str | Path, write: bool = False) -> bool:
        """Check if a plugin can access a file path.

        Args:
            plugin_name: Name of the plugin
            path: File path to check
            write: Whether write access is needed

        Returns:
            True if access is allowed
        """
        if not self.config.enabled:
            return True

        # Check permission
        permission = PluginPermission.FILE_WRITE if write else PluginPermission.FILE_READ
        if not self.permission_manager.check_permission(plugin_name, permission):
            self.record_violation(
                plugin_name,
                "file_access_denied",
                f"No {permission.name} permission for: {path}",
            )
            return False

        # Check allowed paths
        path = Path(path).resolve()
        if self.config.allowed_paths:
            allowed = False
            for allowed_path in self.config.allowed_paths:
                try:
                    path.relative_to(Path(allowed_path).resolve())
                    allowed = True
                    break
                except ValueError:
                    continue
            if not allowed:
                self.record_violation(
                    plugin_name,
                    "file_path_blocked",
                    f"Path not in allowed list: {path}",
                )
                return False

        return True

    def check_network_access(self, plugin_name: str, host: str, is_http: bool = True) -> bool:
        """Check if a plugin can access a network host.

        Args:
            plugin_name: Name of the plugin
            host: Host to access
            is_http: Whether this is HTTP (vs WebSocket)

        Returns:
            True if access is allowed
        """
        if not self.config.enabled:
            return True

        # Check permission
        perm_type = PluginPermission.NETWORK_HTTP if is_http else PluginPermission.NETWORK_WEBSOCKET
        permission = perm_type
        if not self.permission_manager.check_permission(plugin_name, permission):
            self.record_violation(
                plugin_name,
                "network_access_denied",
                f"No {permission.name} permission for: {host}",
            )
            return False

        # Check whitelist
        if self.config.network_whitelist and host not in self.config.network_whitelist:
            self.record_violation(
                plugin_name,
                "network_host_blocked",
                f"Host not in whitelist: {host}",
            )
            return False

        return True

    def check_system_access(self, plugin_name: str, operation: str) -> bool:
        """Check if a plugin can perform a system operation.

        Args:
            plugin_name: Name of the plugin
            operation: Operation type (info, exec, env)

        Returns:
            True if access is allowed
        """
        if not self.config.enabled:
            return True

        permission_map = {
            "info": PluginPermission.SYSTEM_INFO,
            "exec": PluginPermission.SYSTEM_EXEC,
            "env": PluginPermission.SYSTEM_ENV,
        }

        permission = permission_map.get(operation)
        if not permission:
            return True

        if not self.permission_manager.check_permission(plugin_name, permission):
            self.record_violation(
                plugin_name,
                "system_access_denied",
                f"No {permission.name} permission for: {operation}",
            )
            return False

        return True

    def wrap_function(
        self,
        plugin_name: str,
        func: Callable,
        timeout: float | None = None,
    ) -> Callable:
        """Wrap a function with sandbox protections.

        Args:
            plugin_name: Name of the plugin
            func: Function to wrap
            timeout: Execution timeout (None = use config default)

        Returns:
            Wrapped function
        """
        if not self.config.enabled:
            return func

        timeout = timeout or self.config.max_execution_time

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = self.get_context(plugin_name)
            if context:
                context.call_count += 1

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                self.record_violation(
                    plugin_name,
                    "execution_error",
                    f"Error in {func.__name__}: {e}",
                )
                raise
            finally:
                elapsed = time.time() - start_time
                if context:
                    context.total_execution_time += elapsed
                if elapsed > timeout:
                    self.record_violation(
                        plugin_name,
                        "timeout_warning",
                        f"{func.__name__} took {elapsed:.2f}s (limit: {timeout}s)",
                    )

        return wrapper


@dataclass
class PluginContext:
    """Execution context for a plugin.

    Tracks resource usage and provides sandboxed access to system resources.
    """

    plugin_name: str
    sandbox: PluginSandbox
    call_count: int = 0
    total_execution_time: float = 0.0
    created_at: float = field(default_factory=time.time)

    def check_permission(self, permission: PluginPermission) -> bool:
        """Check if the plugin has a permission."""
        return self.sandbox.permission_manager.check_permission(self.plugin_name, permission)

    def require_permission(self, permission: PluginPermission) -> None:
        """Require a permission, raising an error if not granted."""
        self.sandbox.permission_manager.require_permission(self.plugin_name, permission)

    def read_file(self, path: str | Path) -> str:
        """Read a file with permission check.

        Args:
            path: File path

        Returns:
            File contents

        Raises:
            PermissionError: If access is denied
        """
        if not self.sandbox.check_file_access(self.plugin_name, path, write=False):
            raise PermissionError(f"File read access denied: {path}")
        return Path(path).read_text()

    def write_file(self, path: str | Path, content: str) -> None:
        """Write a file with permission check.

        Args:
            path: File path
            content: Content to write

        Raises:
            PermissionError: If access is denied
        """
        if not self.sandbox.check_file_access(self.plugin_name, path, write=True):
            raise PermissionError(f"File write access denied: {path}")
        Path(path).write_text(content)

    def get_env(self, key: str, default: str | None = None) -> str | None:
        """Get an environment variable with permission check.

        Args:
            key: Environment variable name
            default: Default value

        Returns:
            Environment variable value

        Raises:
            PermissionError: If access is denied
        """
        if not self.sandbox.check_system_access(self.plugin_name, "env"):
            raise PermissionError("Environment variable access denied")
        return os.environ.get(key, default)

    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        return {
            "plugin_name": self.plugin_name,
            "call_count": self.call_count,
            "total_execution_time": self.total_execution_time,
            "created_at": self.created_at,
            "uptime": time.time() - self.created_at,
        }


# Global sandbox instance
_sandbox: PluginSandbox | None = None


def get_sandbox() -> PluginSandbox:
    """Get the global sandbox instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = PluginSandbox()
    return _sandbox


def configure_sandbox(config: SandboxConfig) -> PluginSandbox:
    """Configure and return the global sandbox.

    Args:
        config: Sandbox configuration

    Returns:
        Configured sandbox instance
    """
    global _sandbox
    _sandbox = PluginSandbox(config=config)
    return _sandbox
