"""Plugin manifest definitions for dependencies and permissions.

This module provides data structures for declaring plugin dependencies
(both Python packages and other plugins) and permission requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BasePlugin
    from .config_schema import PluginConfigSchema


class PermissionType(str, Enum):
    """Types of permissions a plugin may require.

    These permissions help users understand what a plugin needs access to
    and can be used for security auditing.
    """

    NETWORK_ACCESS = "network"  # HTTP/HTTPS requests
    FILE_READ = "file_read"  # Read local files
    FILE_WRITE = "file_write"  # Write local files
    SCHEDULE_JOBS = "schedule"  # Schedule background jobs
    SEND_MESSAGES = "send_messages"  # Send messages via providers
    ACCESS_CONFIG = "access_config"  # Access bot configuration
    EXTERNAL_API = "external_api"  # Call external APIs
    DATABASE_ACCESS = "database"  # Access databases
    SYSTEM_INFO = "system_info"  # Access system information
    EXECUTE_CODE = "execute_code"  # Execute dynamic code


@dataclass
class PackageDependency:
    """Python package dependency declaration.

    Used to declare Python packages that a plugin requires to function.

    Attributes:
        name: Package name as used with pip
        version: Version specifier (e.g., ">=1.0.0", "~=2.0")
        optional: Whether this dependency is optional
        feature: Feature group this dependency belongs to
        install_hint: Custom installation instructions

    Example:
        ```python
        PackageDependency("httpx", ">=0.27.0")
        PackageDependency("redis", ">=5.0.0", optional=True, feature="caching")
        ```
    """

    name: str
    version: str | None = None
    optional: bool = False
    feature: str | None = None
    install_hint: str | None = None

    def get_pip_spec(self) -> str:
        """Get pip-compatible package specifier.

        Returns:
            String like "httpx>=0.27.0" or just "httpx"
        """
        if self.version:
            return f"{self.name}{self.version}"
        return self.name


@dataclass
class PluginDependency:
    """Dependency on another plugin.

    Used to declare that a plugin requires another plugin to be loaded.

    Attributes:
        plugin_name: Name of the required plugin
        min_version: Minimum required version
        optional: Whether this dependency is optional

    Example:
        ```python
        PluginDependency("core-plugin", min_version="1.0.0")
        PluginDependency("optional-enhancer", optional=True)
        ```
    """

    plugin_name: str
    min_version: str | None = None
    optional: bool = False


@dataclass
class PermissionRequest:
    """Permission request with justification.

    Used to declare what permissions a plugin needs and why.

    Attributes:
        permission: Type of permission requested
        reason: Human-readable explanation of why this is needed
        scope: Optional scope limitation (e.g., specific domains for network)

    Example:
        ```python
        PermissionRequest(
            PermissionType.NETWORK_ACCESS,
            "Access Feishu Calendar API to retrieve events",
            scope="open.feishu.cn"
        )
        ```
    """

    permission: PermissionType
    reason: str
    scope: str | None = None


@dataclass
class PluginManifest:
    """Complete plugin manifest with metadata, dependencies, and permissions.

    The manifest provides comprehensive information about a plugin including
    its identity, requirements, and capabilities.

    Attributes:
        name: Unique plugin identifier
        version: Semantic version string
        description: Human-readable description
        author: Plugin author name or organization
        homepage: URL to plugin homepage or repository
        license: License identifier (e.g., "MIT", "Apache-2.0")
        python_dependencies: List of required Python packages
        plugin_dependencies: List of required plugins
        permissions: List of requested permissions
        config_schema: Reference to configuration schema class
        supports_hot_reload: Whether plugin supports hot reloading
        supports_multi_provider: Whether plugin works with multiple providers
        min_bot_version: Minimum bot version required
        tags: Tags for categorization and discovery

    Example:
        ```python
        manifest = PluginManifest(
            name="feishu-calendar",
            version="2.0.0",
            description="Calendar integration with reminders",
            author="Feishu Bot Team",
            python_dependencies=[
                PackageDependency("httpx", ">=0.27.0"),
            ],
            permissions=[
                PermissionRequest(PermissionType.NETWORK_ACCESS, "API calls"),
                PermissionRequest(PermissionType.SCHEDULE_JOBS, "Event checking"),
            ],
            tags=["calendar", "reminders", "feishu"],
        )
        ```
    """

    # Basic information
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    homepage: str | None = None
    license: str | None = None

    # Dependencies
    python_dependencies: list[PackageDependency] = field(default_factory=list)
    plugin_dependencies: list[PluginDependency] = field(default_factory=list)

    # Permissions
    permissions: list[PermissionRequest] = field(default_factory=list)

    # Configuration
    config_schema: type[PluginConfigSchema] | None = None

    # Capabilities
    supports_hot_reload: bool = True
    supports_multi_provider: bool = True
    min_bot_version: str | None = None

    # Tags for discovery
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_plugin(cls, plugin: BasePlugin) -> PluginManifest:
        """Create manifest from plugin instance by introspection.

        This method inspects a plugin instance for manifest information,
        checking various attributes and methods.

        Args:
            plugin: Plugin instance to inspect

        Returns:
            PluginManifest populated from plugin attributes
        """
        metadata = plugin.metadata()
        plugin_class = plugin.__class__

        manifest = cls(
            name=metadata.name,
            version=metadata.version,
            description=metadata.description,
            author=metadata.author,
        )

        # Check for manifest() method that returns a complete manifest
        if hasattr(plugin_class, "manifest") and callable(plugin_class.manifest):
            try:
                user_manifest = plugin.manifest()
                if isinstance(user_manifest, PluginManifest):
                    return user_manifest
            except Exception:
                pass

        # Check for PYTHON_DEPENDENCIES class attribute
        if hasattr(plugin_class, "PYTHON_DEPENDENCIES"):
            deps = plugin_class.PYTHON_DEPENDENCIES
            if isinstance(deps, list):
                manifest.python_dependencies = [
                    d if isinstance(d, PackageDependency) else PackageDependency(str(d))
                    for d in deps
                ]

        # Check for PLUGIN_DEPENDENCIES class attribute
        if hasattr(plugin_class, "PLUGIN_DEPENDENCIES"):
            deps = plugin_class.PLUGIN_DEPENDENCIES
            if isinstance(deps, list):
                manifest.plugin_dependencies = [
                    d if isinstance(d, PluginDependency) else PluginDependency(str(d)) for d in deps
                ]

        # Check for PERMISSIONS class attribute
        if hasattr(plugin_class, "PERMISSIONS"):
            perms = plugin_class.PERMISSIONS
            if isinstance(perms, list):
                manifest.permissions = [p for p in perms if isinstance(p, PermissionRequest)]

        # Check for config_schema
        if hasattr(plugin_class, "config_schema"):
            schema = plugin_class.config_schema
            if isinstance(schema, type):
                manifest.config_schema = schema

        # Check for additional attributes
        if hasattr(plugin_class, "HOMEPAGE"):
            manifest.homepage = plugin_class.HOMEPAGE
        if hasattr(plugin_class, "LICENSE"):
            manifest.license = plugin_class.LICENSE
        if hasattr(plugin_class, "TAGS"):
            manifest.tags = plugin_class.TAGS
        if hasattr(plugin_class, "MIN_BOT_VERSION"):
            manifest.min_bot_version = plugin_class.MIN_BOT_VERSION
        if hasattr(plugin_class, "SUPPORTS_HOT_RELOAD"):
            manifest.supports_hot_reload = plugin_class.SUPPORTS_HOT_RELOAD
        if hasattr(plugin_class, "SUPPORTS_MULTI_PROVIDER"):
            manifest.supports_multi_provider = plugin_class.SUPPORTS_MULTI_PROVIDER

        return manifest

    def get_required_python_packages(self) -> list[PackageDependency]:
        """Get only required (non-optional) Python dependencies.

        Returns:
            List of required PackageDependency instances
        """
        return [dep for dep in self.python_dependencies if not dep.optional]

    def get_optional_python_packages(self) -> list[PackageDependency]:
        """Get only optional Python dependencies.

        Returns:
            List of optional PackageDependency instances
        """
        return [dep for dep in self.python_dependencies if dep.optional]

    def get_required_plugins(self) -> list[PluginDependency]:
        """Get only required (non-optional) plugin dependencies.

        Returns:
            List of required PluginDependency instances
        """
        return [dep for dep in self.plugin_dependencies if not dep.optional]

    def get_pip_install_command(self) -> str | None:
        """Generate pip install command for required packages.

        Returns:
            Pip install command string, or None if no dependencies
        """
        required = self.get_required_python_packages()
        if not required:
            return None
        packages = " ".join(dep.get_pip_spec() for dep in required)
        return f"pip install {packages}"

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary.

        Returns:
            Dictionary representation of the manifest
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "license": self.license,
            "python_dependencies": [
                {"name": d.name, "version": d.version, "optional": d.optional}
                for d in self.python_dependencies
            ],
            "plugin_dependencies": [
                {"plugin_name": d.plugin_name, "min_version": d.min_version, "optional": d.optional}
                for d in self.plugin_dependencies
            ],
            "permissions": [
                {"permission": p.permission.value, "reason": p.reason, "scope": p.scope}
                for p in self.permissions
            ],
            "supports_hot_reload": self.supports_hot_reload,
            "supports_multi_provider": self.supports_multi_provider,
            "min_bot_version": self.min_bot_version,
            "tags": self.tags,
        }
