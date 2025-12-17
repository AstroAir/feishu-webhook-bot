#!/usr/bin/env python3
"""Plugin Permissions System Example.

This example demonstrates the plugin permission system:
- Permission types and levels
- Requesting permissions for plugins
- Permission checking and enforcement
- Dangerous permission handling
- Permission manager usage

The permission system enables secure plugin execution with controlled access.
"""

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.plugins.permissions import (
    DANGEROUS_PERMISSIONS,
    PERMISSION_LEVELS,
    PermissionLevel,
    PermissionManager,
    PluginPermission,
    PluginPermissionGrant,
    PluginPermissionSet,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Permission Types
# =============================================================================
def demo_permission_types() -> None:
    """Demonstrate available permission types."""
    print("\n" + "=" * 60)
    print("Demo 1: Permission Types")
    print("=" * 60)

    print("\nAll available permissions:")
    for perm in PluginPermission:
        is_dangerous = perm in DANGEROUS_PERMISSIONS
        danger_mark = " [DANGEROUS]" if is_dangerous else ""
        print(f"  - {perm.name}: {perm.value}{danger_mark}")

    print("\n--- Permission Categories ---")
    categories = {
        "Network": [p for p in PluginPermission if p.name.startswith("NETWORK")],
        "File": [p for p in PluginPermission if p.name.startswith("FILE")],
        "System": [p for p in PluginPermission if p.name.startswith("SYSTEM")],
        "Scheduler": [p for p in PluginPermission if p.name.startswith("SCHEDULER")],
        "Config": [p for p in PluginPermission if p.name.startswith("CONFIG")],
        "Database": [p for p in PluginPermission if p.name.startswith("DATABASE")],
        "AI": [p for p in PluginPermission if p.name.startswith("AI")],
        "Event": [p for p in PluginPermission if p.name.startswith("EVENT")],
        "Provider": [p for p in PluginPermission if p.name.startswith("PROVIDER")],
    }

    for category, perms in categories.items():
        if perms:
            print(f"\n  {category}:")
            for perm in perms:
                print(f"    - {perm.name}")


# =============================================================================
# Demo 2: Permission Levels
# =============================================================================
def demo_permission_levels() -> None:
    """Demonstrate permission levels."""
    print("\n" + "=" * 60)
    print("Demo 2: Permission Levels")
    print("=" * 60)

    print("\nPermission levels (from least to most privileged):")
    for level in PermissionLevel:
        perms = PERMISSION_LEVELS.get(level, set())
        print(f"\n  {level.name}:")
        print(f"    Permissions included: {len(perms)}")
        for perm in sorted(perms, key=lambda p: p.name):
            print(f"      - {perm.name}")


# =============================================================================
# Demo 3: Permission Sets
# =============================================================================
def demo_permission_sets() -> None:
    """Demonstrate creating permission sets for plugins."""
    print("\n" + "=" * 60)
    print("Demo 3: Permission Sets")
    print("=" * 60)

    # Create a permission set with required and optional permissions
    perm_set = PluginPermissionSet(
        required={
            PluginPermission.NETWORK_SEND,
            PluginPermission.CONFIG_READ,
        },
        optional={
            PluginPermission.FILE_READ,
            PluginPermission.SCHEDULER_JOBS,
        },
        level=PermissionLevel.STANDARD,
    )

    print("\nPermission set for a plugin:")
    print(f"  Required permissions: {[p.name for p in perm_set.required]}")
    print(f"  Optional permissions: {[p.name for p in perm_set.optional]}")
    print(f"  Permission level: {perm_set.level.name if perm_set.level else 'None'}")

    print("\n  All permissions (including level):")
    for perm in perm_set.get_all_permissions():
        print(f"    - {perm.name}")

    print(f"\n  Has dangerous permissions: {perm_set.has_dangerous_permissions()}")

    # Permission set with dangerous permissions
    dangerous_set = PluginPermissionSet(
        required={
            PluginPermission.SYSTEM_EXEC,
            PluginPermission.FILE_WRITE,
        }
    )

    print("\n--- Permission set with dangerous permissions ---")
    print(f"  Has dangerous: {dangerous_set.has_dangerous_permissions()}")
    print(f"  Dangerous permissions: {[p.name for p in dangerous_set.get_dangerous_permissions()]}")


# =============================================================================
# Demo 4: Permission Manager
# =============================================================================
def demo_permission_manager() -> None:
    """Demonstrate using the permission manager."""
    print("\n" + "=" * 60)
    print("Demo 4: Permission Manager")
    print("=" * 60)

    # Create a permission manager
    pm = PermissionManager()

    # Register plugin permissions
    plugin_perms = PluginPermissionSet(
        required={
            PluginPermission.NETWORK_SEND,
            PluginPermission.NETWORK_HTTP,
            PluginPermission.CONFIG_READ,
        },
        optional={
            PluginPermission.FILE_READ,
        },
    )

    pm.register_plugin_permissions("my-plugin", plugin_perms)
    print("\nRegistered permissions for 'my-plugin'")

    # Auto-grant non-dangerous permissions
    grant = pm.grant_permissions("my-plugin", auto_grant=True)
    print("\nAuto-granted permissions:")
    for perm in grant.granted:
        print(f"  - {perm.name}")

    # Check permissions
    print("\n--- Permission checks ---")
    perms_to_check = [
        PluginPermission.NETWORK_SEND,
        PluginPermission.FILE_READ,
        PluginPermission.SYSTEM_EXEC,
    ]

    for perm in perms_to_check:
        has_perm = pm.check_permission("my-plugin", perm)
        status = "GRANTED" if has_perm else "DENIED"
        print(f"  {perm.name}: {status}")

    # Validate plugin permissions
    is_valid, missing = pm.validate_plugin_permissions("my-plugin")
    print(f"\n  All required permissions granted: {is_valid}")
    if missing:
        print(f"  Missing permissions: {missing}")


# =============================================================================
# Demo 5: Dangerous Permission Handling
# =============================================================================
def demo_dangerous_permissions() -> None:
    """Demonstrate handling dangerous permissions."""
    print("\n" + "=" * 60)
    print("Demo 5: Dangerous Permission Handling")
    print("=" * 60)

    pm = PermissionManager()

    # Register plugin with dangerous permissions
    dangerous_perms = PluginPermissionSet(
        required={
            PluginPermission.NETWORK_SEND,
            PluginPermission.SYSTEM_EXEC,  # Dangerous!
            PluginPermission.FILE_WRITE,  # Dangerous!
        }
    )

    pm.register_plugin_permissions("dangerous-plugin", dangerous_perms)

    # Auto-grant will skip dangerous permissions
    pm.grant_permissions("dangerous-plugin", auto_grant=True)

    print("\nAfter auto-grant (dangerous permissions skipped):")
    grant = pm.get_grant("dangerous-plugin")
    print(f"  Granted: {[p.name for p in grant.granted]}")

    # Get pending dangerous approvals
    pending = pm.get_pending_dangerous_approvals("dangerous-plugin")
    print(f"  Pending dangerous approvals: {[p.name for p in pending]}")

    # Explicitly approve dangerous permissions
    print("\n--- Explicitly approving dangerous permissions ---")
    grant.approve_dangerous(PluginPermission.SYSTEM_EXEC)
    print("  Approved SYSTEM_EXEC")
    print(f"  Approved dangerous: {[p.name for p in grant.approved_dangerous]}")

    # Validate again
    is_valid, missing = pm.validate_plugin_permissions("dangerous-plugin")
    print(f"\n  All permissions granted: {is_valid}")
    if missing:
        print(f"  Still missing: {missing}")


# =============================================================================
# Demo 6: Permission Grants
# =============================================================================
def demo_permission_grants() -> None:
    """Demonstrate permission grant operations."""
    print("\n" + "=" * 60)
    print("Demo 6: Permission Grants")
    print("=" * 60)

    # Create a grant manually
    grant = PluginPermissionGrant(plugin_name="test-plugin")

    # Grant permissions
    grant.grant(PluginPermission.NETWORK_SEND)
    grant.grant(PluginPermission.CONFIG_READ)
    print("\nGranted permissions:")
    for perm in grant.granted:
        print(f"  - {perm.name}")

    # Deny a permission
    grant.deny(PluginPermission.FILE_WRITE)
    print("\nDenied permissions:")
    for perm in grant.denied:
        print(f"  - {perm.name}")

    # Check if granted
    print("\n--- Permission checks ---")
    print(f"  NETWORK_SEND granted: {grant.is_granted(PluginPermission.NETWORK_SEND)}")
    print(f"  FILE_WRITE granted: {grant.is_granted(PluginPermission.FILE_WRITE)}")
    print(f"  SYSTEM_EXEC granted: {grant.is_granted(PluginPermission.SYSTEM_EXEC)}")

    # Convert to dict
    print("\n--- Grant as dictionary ---")
    data = grant.to_dict()
    print(f"  Plugin: {data['plugin_name']}")
    print(f"  Granted: {data['granted']}")
    print(f"  Denied: {data['denied']}")


# =============================================================================
# Demo 7: Real-World Plugin Permission Example
# =============================================================================
def demo_real_world_example() -> None:
    """Demonstrate a real-world plugin permission scenario."""
    print("\n" + "=" * 60)
    print("Demo 7: Real-World Plugin Permission Example")
    print("=" * 60)

    pm = PermissionManager()

    # Calendar plugin permissions
    calendar_perms = PluginPermissionSet(
        required={
            PluginPermission.NETWORK_HTTP,  # For API calls
            PluginPermission.CONFIG_READ,  # For reading settings
            PluginPermission.SCHEDULER_JOBS,  # For scheduling reminders
            PluginPermission.EVENT_EMIT,  # For emitting calendar events
        },
        optional={
            PluginPermission.DATABASE_READ,  # For caching
            PluginPermission.DATABASE_WRITE,  # For caching
        },
    )

    pm.register_plugin_permissions("feishu-calendar", calendar_perms)
    pm.grant_permissions("feishu-calendar", auto_grant=True)

    print("\nFeishu Calendar Plugin Permissions:")
    grant = pm.get_grant("feishu-calendar")
    print(f"  Granted: {[p.name for p in grant.granted]}")

    is_valid, missing = pm.validate_plugin_permissions("feishu-calendar")
    print(f"  Ready to run: {is_valid}")

    # AI plugin with dangerous permissions
    ai_perms = PluginPermissionSet(
        required={
            PluginPermission.AI_CHAT,
            PluginPermission.AI_TOOLS,
            PluginPermission.NETWORK_HTTP,
            PluginPermission.SYSTEM_EXEC,  # For running code (dangerous!)
        },
    )

    pm.register_plugin_permissions("ai-assistant", ai_perms)
    pm.grant_permissions("ai-assistant", auto_grant=True)

    print("\nAI Assistant Plugin Permissions:")
    grant = pm.get_grant("ai-assistant")
    print(f"  Granted: {[p.name for p in grant.granted]}")

    pending = pm.get_pending_dangerous_approvals("ai-assistant")
    print(f"  Pending dangerous: {[p.name for p in pending]}")

    is_valid, missing = pm.validate_plugin_permissions("ai-assistant")
    print(f"  Ready to run: {is_valid}")
    if not is_valid:
        print(f"  Missing: {missing}")
        print("  -> User must explicitly approve SYSTEM_EXEC permission")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all plugin permission demonstrations."""
    print("=" * 60)
    print("Plugin Permissions System Examples")
    print("=" * 60)

    demos = [
        ("Permission Types", demo_permission_types),
        ("Permission Levels", demo_permission_levels),
        ("Permission Sets", demo_permission_sets),
        ("Permission Manager", demo_permission_manager),
        ("Dangerous Permission Handling", demo_dangerous_permissions),
        ("Permission Grants", demo_permission_grants),
        ("Real-World Example", demo_real_world_example),
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
