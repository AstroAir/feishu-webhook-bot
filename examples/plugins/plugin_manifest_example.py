#!/usr/bin/env python3
"""Plugin Manifest Example.

This example demonstrates the plugin manifest system:
- Defining plugin metadata
- Version information
- Author and license
- Dependencies declaration
- Permissions and capabilities

The manifest provides essential information about a plugin.
"""

import json
from typing import Any

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.plugins.manifest import (
    PackageDependency,
    PermissionRequest,
    PermissionType,
    PluginDependency,
    PluginManifest,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


def demo_basic_manifest() -> None:
    """Demonstrate basic plugin manifest."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Plugin Manifest")
    print("=" * 60)

    manifest = PluginManifest(
        name="my-plugin",
        version="1.0.0",
        description="A simple example plugin",
        author="Developer Name",
    )

    print("Basic manifest:")
    print(f"  Name: {manifest.name}")
    print(f"  Version: {manifest.version}")
    print(f"  Description: {manifest.description}")
    print(f"  Author: {manifest.author}")


def demo_complete_manifest() -> None:
    """Demonstrate a complete plugin manifest."""
    print("\n" + "=" * 60)
    print("Demo 2: Complete Manifest")
    print("=" * 60)

    manifest = PluginManifest(
        name="feishu-calendar-sync",
        version="2.1.0",
        description="Synchronize Feishu calendar events",
        author="Feishu Bot Team",
        homepage="https://github.com/example/feishu-calendar-sync",
        license="MIT",
        min_bot_version="1.0.0",
        supports_hot_reload=True,
        supports_multi_provider=True,
        tags=["calendar", "sync", "feishu"],
    )

    print("Complete manifest:")
    print(f"  Name: {manifest.name}")
    print(f"  Version: {manifest.version}")
    print(f"  Description: {manifest.description}")
    print(f"  Author: {manifest.author}")
    print(f"  Homepage: {manifest.homepage}")
    print(f"  License: {manifest.license}")
    print(f"  Min bot version: {manifest.min_bot_version}")
    print(f"  Tags: {', '.join(manifest.tags)}")


def demo_manifest_dependencies() -> None:
    """Demonstrate dependencies in manifest."""
    print("\n" + "=" * 60)
    print("Demo 3: Dependencies in Manifest")
    print("=" * 60)

    manifest = PluginManifest(
        name="advanced-plugin",
        version="1.0.0",
        description="Plugin with dependencies",
        author="Developer",
        python_dependencies=[
            PackageDependency(name="requests", version=">=2.28.0"),
            PackageDependency(name="pydantic", version=">=2.0.0"),
        ],
        plugin_dependencies=[
            PluginDependency(name="base-plugin", version=">=1.0.0"),
        ],
    )

    print("Manifest with dependencies:")
    print("\n  Python dependencies:")
    for dep in manifest.python_dependencies:
        print(f"    - {dep.name}{dep.version}")

    print("\n  Plugin dependencies:")
    for dep in manifest.plugin_dependencies:
        print(f"    - {dep.name}{dep.version}")


def demo_plugin_permissions() -> None:
    """Demonstrate plugin permissions."""
    print("\n" + "=" * 60)
    print("Demo 4: Plugin Permissions")
    print("=" * 60)

    manifest = PluginManifest(
        name="secure-plugin",
        version="1.0.0",
        description="Plugin with permission requirements",
        author="Developer",
        permissions=[
            PermissionRequest(
                permission=PermissionType.NETWORK_ACCESS,
                reason="Required for API calls",
            ),
            PermissionRequest(
                permission=PermissionType.SCHEDULE_JOBS,
                reason="Required for scheduling tasks",
            ),
        ],
    )

    print("Plugin permissions:")
    for perm in manifest.permissions:
        print(f"  - {perm.permission.value}: {perm.reason}")

    print("\nAvailable permission types:")
    for perm_type in PermissionType:
        print(f"  - {perm_type.value}")


def demo_real_world_manifest() -> None:
    """Demonstrate a real-world plugin manifest."""
    print("\n" + "=" * 60)
    print("Demo 5: Real-World Plugin Manifest")
    print("=" * 60)

    manifest = PluginManifest(
        name="feishu-calendar",
        version="2.0.0",
        description="Full-featured Feishu Calendar integration",
        author="Feishu Bot Team",
        homepage="https://github.com/example/feishu-calendar",
        license="MIT",
        python_dependencies=[
            PackageDependency(name="httpx", version=">=0.27.0"),
        ],
        permissions=[
            PermissionRequest(
                permission=PermissionType.NETWORK_ACCESS,
                reason="Required for Feishu API calls",
            ),
        ],
        supports_hot_reload=True,
        tags=["feishu", "calendar", "events"],
    )

    print("Real-world plugin manifest:")
    print(f"  Name: {manifest.name}")
    print(f"  Version: {manifest.version}")
    print(f"  Description: {manifest.description}")
    print(f"  Tags: {', '.join(manifest.tags)}")


def print_json(obj: Any, indent: int = 2) -> None:
    """Pretty print a JSON-serializable object."""
    print(json.dumps(obj, indent=indent, ensure_ascii=False, default=str))


def main() -> None:
    """Run all plugin manifest demonstrations."""
    print("=" * 60)
    print("Plugin Manifest Examples")
    print("=" * 60)

    demos = [
        ("Basic Plugin Manifest", demo_basic_manifest),
        ("Complete Manifest", demo_complete_manifest),
        ("Dependencies in Manifest", demo_manifest_dependencies),
        ("Plugin Permissions", demo_plugin_permissions),
        ("Real-World Plugin Manifest", demo_real_world_manifest),
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
