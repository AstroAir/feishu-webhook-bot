"""Plugin dependency checker.

This module provides tools for checking and validating plugin dependencies,
both Python packages and other plugins.
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..core.logger import get_logger

if TYPE_CHECKING:
    from .base import BasePlugin
    from .manifest import PackageDependency, PluginDependency, PluginManifest

logger = get_logger("plugin.dependency_checker")


@dataclass
class DependencyStatus:
    """Status of a single dependency check.

    Attributes:
        satisfied: Whether the dependency is satisfied
        name: Name of the dependency (package or plugin)
        required_version: Version requirement string
        installed_version: Currently installed version (if any)
        error: Error message if check failed
        install_command: Suggested installation command
    """

    satisfied: bool
    name: str
    required_version: str | None = None
    installed_version: str | None = None
    error: str | None = None
    install_command: str | None = None


@dataclass
class DependencyCheckResult:
    """Result of checking all dependencies for a plugin.

    Attributes:
        plugin_name: Name of the plugin being checked
        all_satisfied: Whether all dependencies are satisfied
        python_deps: Status of each Python package dependency
        plugin_deps: Status of each plugin dependency
        missing_packages: Names of missing Python packages
        missing_plugins: Names of missing plugins
    """

    plugin_name: str
    all_satisfied: bool
    python_deps: list[DependencyStatus] = field(default_factory=list)
    plugin_deps: list[DependencyStatus] = field(default_factory=list)
    missing_packages: list[str] = field(default_factory=list)
    missing_plugins: list[str] = field(default_factory=list)


class DependencyChecker:
    """Checks and validates plugin dependencies.

    This class provides methods for checking Python package dependencies
    and plugin dependencies against what is currently installed/loaded.

    Example:
        ```python
        checker = DependencyChecker(loaded_plugins)

        # Check a single package
        status = checker.check_python_dependency(PackageDependency("httpx", ">=0.27.0"))
        if not status.satisfied:
            print(f"Missing: {status.name} - {status.install_command}")

        # Check all dependencies for a plugin
        result = checker.check_manifest(manifest)
        if not result.all_satisfied:
            for pkg in result.missing_packages:
                print(f"Missing package: {pkg}")
        ```
    """

    def __init__(self, loaded_plugins: dict[str, BasePlugin] | None = None):
        """Initialize the dependency checker.

        Args:
            loaded_plugins: Dictionary of currently loaded plugins (name -> instance)
        """
        self._loaded_plugins = loaded_plugins or {}

    def check_python_dependency(self, dep: PackageDependency) -> DependencyStatus:
        """Check if a Python package dependency is satisfied.

        Uses importlib.metadata to check if the package is installed
        and packaging library to verify version requirements.

        Args:
            dep: Package dependency to check

        Returns:
            DependencyStatus with check results
        """
        try:
            installed_version = importlib.metadata.version(dep.name)

            # Check version requirement if specified
            if dep.version:
                satisfied = self._version_satisfies(installed_version, dep.version)
                if not satisfied:
                    return DependencyStatus(
                        satisfied=False,
                        name=dep.name,
                        required_version=dep.version,
                        installed_version=installed_version,
                        error=f"Version {installed_version} does not satisfy {dep.version}",
                        install_command=f"pip install '{dep.get_pip_spec()}'",
                    )
            else:
                satisfied = True

            return DependencyStatus(
                satisfied=True,
                name=dep.name,
                required_version=dep.version,
                installed_version=installed_version,
            )

        except importlib.metadata.PackageNotFoundError:
            return DependencyStatus(
                satisfied=False,
                name=dep.name,
                required_version=dep.version,
                installed_version=None,
                error=f"Package '{dep.name}' is not installed",
                install_command=f"pip install '{dep.get_pip_spec()}'",
            )
        except Exception as e:
            return DependencyStatus(
                satisfied=False,
                name=dep.name,
                required_version=dep.version,
                installed_version=None,
                error=f"Error checking package: {e}",
                install_command=f"pip install '{dep.get_pip_spec()}'",
            )

    def check_plugin_dependency(self, dep: PluginDependency) -> DependencyStatus:
        """Check if a plugin dependency is satisfied.

        Args:
            dep: Plugin dependency to check

        Returns:
            DependencyStatus with check results
        """
        plugin = self._loaded_plugins.get(dep.plugin_name)

        if plugin is None:
            return DependencyStatus(
                satisfied=False,
                name=dep.plugin_name,
                required_version=dep.min_version,
                installed_version=None,
                error=f"Plugin '{dep.plugin_name}' is not loaded",
            )

        try:
            metadata = plugin.metadata()
            installed_version = metadata.version

            # Check version requirement if specified
            if dep.min_version:
                satisfied = self._version_satisfies(installed_version, f">={dep.min_version}")
                if not satisfied:
                    return DependencyStatus(
                        satisfied=False,
                        name=dep.plugin_name,
                        required_version=dep.min_version,
                        installed_version=installed_version,
                        error=f"Plugin version {installed_version} < required {dep.min_version}",
                    )

            return DependencyStatus(
                satisfied=True,
                name=dep.plugin_name,
                required_version=dep.min_version,
                installed_version=installed_version,
            )

        except Exception as e:
            return DependencyStatus(
                satisfied=False,
                name=dep.plugin_name,
                required_version=dep.min_version,
                installed_version=None,
                error=f"Error checking plugin: {e}",
            )

    def check_manifest(self, manifest: PluginManifest) -> DependencyCheckResult:
        """Check all dependencies declared in a manifest.

        Args:
            manifest: Plugin manifest with dependency declarations

        Returns:
            DependencyCheckResult with comprehensive status
        """
        python_results: list[DependencyStatus] = []
        plugin_results: list[DependencyStatus] = []
        missing_packages: list[str] = []
        missing_plugins: list[str] = []

        # Check Python dependencies (skip optional ones for "all_satisfied")
        for dep in manifest.python_dependencies:
            status = self.check_python_dependency(dep)
            python_results.append(status)
            if not status.satisfied and not dep.optional:
                missing_packages.append(dep.name)

        # Check plugin dependencies (skip optional ones for "all_satisfied")
        for dep in manifest.plugin_dependencies:
            status = self.check_plugin_dependency(dep)
            plugin_results.append(status)
            if not status.satisfied and not dep.optional:
                missing_plugins.append(dep.plugin_name)

        all_satisfied = not (missing_packages or missing_plugins)

        return DependencyCheckResult(
            plugin_name=manifest.name,
            all_satisfied=all_satisfied,
            python_deps=python_results,
            plugin_deps=plugin_results,
            missing_packages=missing_packages,
            missing_plugins=missing_plugins,
        )

    def check_all_plugins(
        self, manifests: dict[str, PluginManifest]
    ) -> dict[str, DependencyCheckResult]:
        """Check dependencies for multiple plugins.

        Args:
            manifests: Dictionary mapping plugin names to manifests

        Returns:
            Dictionary mapping plugin names to check results
        """
        results: dict[str, DependencyCheckResult] = {}
        for plugin_name, manifest in manifests.items():
            results[plugin_name] = self.check_manifest(manifest)
        return results

    def get_install_commands(self, result: DependencyCheckResult) -> list[str]:
        """Generate pip install commands for missing packages.

        Args:
            result: Dependency check result

        Returns:
            List of pip install command strings
        """
        commands: list[str] = []
        for status in result.python_deps:
            if not status.satisfied and status.install_command:
                commands.append(status.install_command)
        return commands

    def get_all_missing_packages(self, results: dict[str, DependencyCheckResult]) -> list[str]:
        """Get unique list of all missing packages across multiple plugins.

        Args:
            results: Dictionary of check results

        Returns:
            Deduplicated list of missing package names
        """
        missing: set[str] = set()
        for result in results.values():
            missing.update(result.missing_packages)
        return sorted(missing)

    @staticmethod
    def _version_satisfies(installed: str, required: str) -> bool:
        """Check if installed version satisfies requirement.

        Uses the packaging library for proper version comparison.

        Args:
            installed: Installed version string
            required: Version requirement specifier

        Returns:
            True if installed version satisfies requirement
        """
        try:
            from packaging.specifiers import SpecifierSet
            from packaging.version import Version

            spec = SpecifierSet(required)
            version = Version(installed)
            return version in spec
        except ImportError:
            # Fallback: simple string comparison if packaging not available
            logger.warning("packaging library not available, using simple version comparison")
            # Handle common cases
            if required.startswith(">="):
                return installed >= required[2:]
            if required.startswith("<="):
                return installed <= required[2:]
            if required.startswith("=="):
                return installed == required[2:]
            if required.startswith(">"):
                return installed > required[1:]
            if required.startswith("<"):
                return installed < required[1:]
            return True
        except Exception as e:
            logger.warning("Version comparison failed: %s", e)
            return True  # Assume satisfied on error

    def update_loaded_plugins(self, plugins: dict[str, BasePlugin]) -> None:
        """Update the set of loaded plugins.

        Args:
            plugins: New dictionary of loaded plugins
        """
        self._loaded_plugins = plugins
