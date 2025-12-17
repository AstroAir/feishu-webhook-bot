#!/usr/bin/env python3
"""Plugin Dependency Checker Example.

This example demonstrates the plugin dependency checking system:
- Checking Python package dependencies
- Checking plugin dependencies
- Version comparison and validation
- Generating install commands
- Working with plugin manifests

The dependency checker ensures plugins have all required dependencies.
"""

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.plugins.dependency_checker import (
    DependencyChecker,
    DependencyCheckResult,
    DependencyStatus,
)
from feishu_webhook_bot.plugins.manifest import (
    PackageDependency,
    PluginDependency,
    PluginManifest,
)

setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Basic Python Package Check
# =============================================================================
def demo_basic_check() -> None:
    """Demonstrate basic Python package dependency checking."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Python Package Check")
    print("=" * 60)

    checker = DependencyChecker()

    # Check some common packages
    packages = [
        PackageDependency(name="pydantic", version=">=2.0.0"),
        PackageDependency(name="httpx", version=">=0.27.0"),
        PackageDependency(name="pyyaml", version=">=6.0"),
        PackageDependency(name="nonexistent-package", version=">=1.0.0"),
    ]

    print("\nChecking package dependencies:")
    for pkg in packages:
        status = checker.check_python_dependency(pkg)
        symbol = "✓" if status.satisfied else "✗"
        version_str = pkg.version if pkg.version else "(any)"
        print(f"  {symbol} {pkg.name} {version_str}")
        if status.installed_version:
            print(f"      Installed: {status.installed_version}")
        if status.error:
            print(f"      Error: {status.error}")
        if status.install_command:
            print(f"      Install: {status.install_command}")


# =============================================================================
# Demo 2: Version Comparison
# =============================================================================
def demo_version_comparison() -> None:
    """Demonstrate version comparison logic."""
    print("\n" + "=" * 60)
    print("Demo 2: Version Comparison")
    print("=" * 60)

    test_cases = [
        ("1.0.0", ">=1.0.0", True),
        ("1.1.0", ">=1.0.0", True),
        ("0.9.0", ">=1.0.0", False),
        ("2.0.0", "==2.0.0", True),
        ("2.0.1", "==2.0.0", False),
        ("1.5.0", ">=1.0.0,<2.0.0", True),
        ("2.5.0", ">=1.0.0,<2.0.0", False),
    ]

    print("\nVersion comparison tests:")
    for installed, required, expected in test_cases:
        result = DependencyChecker._version_satisfies(installed, required)
        status = "PASS" if result == expected else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {installed} satisfies {required}: {result} [{status}]")


# =============================================================================
# Demo 3: Plugin Dependency Check
# =============================================================================
def demo_plugin_dependency() -> None:
    """Demonstrate plugin dependency checking."""
    print("\n" + "=" * 60)
    print("Demo 3: Plugin Dependency Check")
    print("=" * 60)

    # Simulate loaded plugins
    from unittest.mock import MagicMock

    mock_core_plugin = MagicMock()
    mock_core_plugin.metadata.return_value.version = "2.0.0"

    mock_auth_plugin = MagicMock()
    mock_auth_plugin.metadata.return_value.version = "1.5.0"

    loaded_plugins = {
        "core-plugin": mock_core_plugin,
        "auth-plugin": mock_auth_plugin,
    }

    checker = DependencyChecker(loaded_plugins)

    # Check plugin dependencies
    plugin_deps = [
        PluginDependency(plugin_name="core-plugin", min_version="1.0.0"),
        PluginDependency(plugin_name="auth-plugin", min_version="2.0.0"),
        PluginDependency(plugin_name="missing-plugin"),
    ]

    print("\nChecking plugin dependencies:")
    for dep in plugin_deps:
        status = checker.check_plugin_dependency(dep)
        symbol = "✓" if status.satisfied else "✗"
        version_str = f">={dep.min_version}" if dep.min_version else "(any)"
        print(f"  {symbol} {dep.plugin_name} {version_str}")
        if status.installed_version:
            print(f"      Loaded version: {status.installed_version}")
        if status.error:
            print(f"      Error: {status.error}")


# =============================================================================
# Demo 4: Manifest Dependency Check
# =============================================================================
def demo_manifest_check() -> None:
    """Demonstrate checking all dependencies in a manifest."""
    print("\n" + "=" * 60)
    print("Demo 4: Manifest Dependency Check")
    print("=" * 60)

    # Create a plugin manifest
    manifest = PluginManifest(
        name="calendar-plugin",
        version="1.0.0",
        description="Calendar integration plugin",
        python_dependencies=[
            PackageDependency(name="httpx", version=">=0.27.0"),
            PackageDependency(name="pydantic", version=">=2.0.0"),
            PackageDependency(name="redis", version=">=5.0.0", optional=True),
        ],
        plugin_dependencies=[
            PluginDependency(plugin_name="core-plugin", min_version="1.0.0"),
        ],
    )

    # Simulate loaded plugins
    from unittest.mock import MagicMock

    mock_core = MagicMock()
    mock_core.metadata.return_value.version = "2.0.0"

    checker = DependencyChecker({"core-plugin": mock_core})
    result = checker.check_manifest(manifest)

    print(f"\nManifest check for: {manifest.name}")
    print(f"  All satisfied: {result.all_satisfied}")

    print("\n  Python dependencies:")
    for dep_status in result.python_deps:
        symbol = "✓" if dep_status.satisfied else "✗"
        print(f"    {symbol} {dep_status.name}")

    print("\n  Plugin dependencies:")
    for dep_status in result.plugin_deps:
        symbol = "✓" if dep_status.satisfied else "✗"
        print(f"    {symbol} {dep_status.name}")

    if result.missing_packages:
        print(f"\n  Missing packages: {result.missing_packages}")

    if result.missing_plugins:
        print(f"  Missing plugins: {result.missing_plugins}")


# =============================================================================
# Demo 5: Generate Install Commands
# =============================================================================
def demo_install_commands() -> None:
    """Demonstrate generating install commands."""
    print("\n" + "=" * 60)
    print("Demo 5: Generate Install Commands")
    print("=" * 60)

    # Create result with missing dependencies
    result = DependencyCheckResult(
        plugin_name="test-plugin",
        all_satisfied=False,
        python_deps=[
            DependencyStatus(
                satisfied=False,
                name="httpx",
                required_version=">=0.27.0",
                install_command="pip install 'httpx>=0.27.0'",
            ),
            DependencyStatus(
                satisfied=False,
                name="redis",
                required_version=">=5.0.0",
                install_command="pip install 'redis>=5.0.0'",
            ),
            DependencyStatus(
                satisfied=True,
                name="pydantic",
                installed_version="2.5.0",
            ),
        ],
        missing_packages=["httpx", "redis"],
    )

    checker = DependencyChecker()
    commands = checker.get_install_commands(result)

    print("\nInstall commands for missing dependencies:")
    for cmd in commands:
        print(f"  $ {cmd}")

    # Combined command
    if commands:
        packages = " ".join(
            f"'{dep.name}{dep.required_version}'"
            for dep in result.python_deps
            if not dep.satisfied and dep.required_version
        )
        print(f"\n  Combined: pip install {packages}")


# =============================================================================
# Demo 6: Real-World Plugin Check
# =============================================================================
def demo_real_world() -> None:
    """Demonstrate a real-world plugin dependency scenario."""
    print("\n" + "=" * 60)
    print("Demo 6: Real-World Plugin Check")
    print("=" * 60)

    # Feishu Calendar plugin manifest
    calendar_manifest = PluginManifest(
        name="feishu-calendar",
        version="2.0.0",
        description="Feishu Calendar integration",
        author="Bot Team",
        python_dependencies=[
            PackageDependency(name="httpx", version=">=0.27.0"),
            PackageDependency(name="pydantic", version=">=2.0.0"),
            PackageDependency(name="apscheduler", version=">=3.10.0"),
        ],
    )

    checker = DependencyChecker()
    result = checker.check_manifest(calendar_manifest)

    print(f"\nPlugin: {calendar_manifest.name} v{calendar_manifest.version}")
    print(f"Ready to install: {result.all_satisfied}")

    if not result.all_satisfied:
        print("\nMissing dependencies:")
        for pkg in result.missing_packages:
            print(f"  - {pkg}")

        # Get pip install command from manifest
        pip_cmd = calendar_manifest.get_pip_install_command()
        if pip_cmd:
            print(f"\nInstall with: {pip_cmd}")
    else:
        print("\nAll dependencies satisfied!")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all plugin dependency checker demonstrations."""
    print("=" * 60)
    print("Plugin Dependency Checker Examples")
    print("=" * 60)

    demos = [
        ("Basic Python Package Check", demo_basic_check),
        ("Version Comparison", demo_version_comparison),
        ("Plugin Dependency Check", demo_plugin_dependency),
        ("Manifest Dependency Check", demo_manifest_check),
        ("Generate Install Commands", demo_install_commands),
        ("Real-World Plugin Check", demo_real_world),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
