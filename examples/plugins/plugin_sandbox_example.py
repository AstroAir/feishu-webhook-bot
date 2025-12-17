#!/usr/bin/env python3
"""Plugin Sandbox System Example.

This example demonstrates the plugin sandbox system:
- Sandbox configuration
- File access control
- Network access control
- System access control
- Violation tracking
- Plugin context usage

The sandbox system enables secure plugin execution with controlled resource access.
"""

import tempfile
from pathlib import Path

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.plugins.permissions import (
    PermissionManager,
    PluginPermission,
)
from feishu_webhook_bot.plugins.sandbox import (
    PluginSandbox,
    SandboxConfig,
    configure_sandbox,
    get_sandbox,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Sandbox Configuration
# =============================================================================
def demo_sandbox_config() -> None:
    """Demonstrate sandbox configuration options."""
    print("\n" + "=" * 60)
    print("Demo 1: Sandbox Configuration")
    print("=" * 60)

    # Default configuration
    default_config = SandboxConfig()
    print("\nDefault sandbox configuration:")
    print(f"  Enabled: {default_config.enabled}")
    print(f"  Max execution time: {default_config.max_execution_time}s")
    print(f"  Max memory: {default_config.max_memory_mb}MB (0 = unlimited)")
    print(f"  Allowed paths: {default_config.allowed_paths}")
    print(f"  Blocked modules: {default_config.blocked_modules[:5]}...")
    print(f"  Network whitelist: {default_config.network_whitelist}")

    # Custom configuration
    custom_config = SandboxConfig(
        enabled=True,
        max_execution_time=60.0,
        max_memory_mb=256,
        allowed_paths=["/tmp", "/data/plugins"],
        blocked_modules=["subprocess", "os.system", "eval", "exec"],
        network_whitelist=["api.feishu.cn", "open.feishu.cn", "localhost"],
    )

    print("\nCustom sandbox configuration:")
    print(f"  Enabled: {custom_config.enabled}")
    print(f"  Max execution time: {custom_config.max_execution_time}s")
    print(f"  Max memory: {custom_config.max_memory_mb}MB")
    print(f"  Allowed paths: {custom_config.allowed_paths}")
    print(f"  Network whitelist: {custom_config.network_whitelist}")


# =============================================================================
# Demo 2: Creating a Sandbox
# =============================================================================
def demo_create_sandbox() -> None:
    """Demonstrate creating and configuring a sandbox."""
    print("\n" + "=" * 60)
    print("Demo 2: Creating a Sandbox")
    print("=" * 60)

    # Create permission manager with some permissions
    pm = PermissionManager()
    pm.grant_permissions(
        "demo-plugin",
        permissions={
            PluginPermission.FILE_READ,
            PluginPermission.NETWORK_HTTP,
            PluginPermission.SYSTEM_INFO,
        },
    )

    # Create sandbox with permission manager
    config = SandboxConfig(
        enabled=True,
        allowed_paths=[tempfile.gettempdir()],
        network_whitelist=["api.example.com"],
    )

    sandbox = PluginSandbox(config=config, permission_manager=pm)
    print("\nSandbox created with:")
    print(f"  Enabled: {sandbox.config.enabled}")
    print(f"  Permission manager: {sandbox.permission_manager is not None}")

    # Create plugin context
    context = sandbox.create_context("demo-plugin")
    print(f"\nPlugin context created for: {context.plugin_name}")
    print(f"  Created at: {context.created_at}")


# =============================================================================
# Demo 3: File Access Control
# =============================================================================
def demo_file_access() -> None:
    """Demonstrate file access control."""
    print("\n" + "=" * 60)
    print("Demo 3: File Access Control")
    print("=" * 60)

    pm = PermissionManager()
    pm.grant_permissions(
        "file-plugin",
        permissions={
            PluginPermission.FILE_READ,
            PluginPermission.FILE_WRITE,
        },
    )

    sandbox = PluginSandbox(
        config=SandboxConfig(
            enabled=True,
            allowed_paths=[tempfile.gettempdir()],
        ),
        permission_manager=pm,
    )

    # Test file access checks
    temp_path = Path(tempfile.gettempdir()) / "test.txt"
    system_path = Path("/etc/passwd")

    print("\nFile access checks:")

    # Allowed path - read
    allowed = sandbox.check_file_access("file-plugin", temp_path, write=False)
    print(f"  Read {temp_path}: {'ALLOWED' if allowed else 'DENIED'}")

    # Allowed path - write
    allowed = sandbox.check_file_access("file-plugin", temp_path, write=True)
    print(f"  Write {temp_path}: {'ALLOWED' if allowed else 'DENIED'}")

    # Blocked path
    allowed = sandbox.check_file_access("file-plugin", system_path, write=False)
    print(f"  Read {system_path}: {'ALLOWED' if allowed else 'DENIED'}")

    # Check violations
    violations = sandbox.get_violations("file-plugin")
    if violations:
        print(f"\n  Violations recorded: {len(violations)}")
        for v in violations:
            print(f"    - {v.violation_type}: {v.details[:50]}...")


# =============================================================================
# Demo 4: Network Access Control
# =============================================================================
def demo_network_access() -> None:
    """Demonstrate network access control."""
    print("\n" + "=" * 60)
    print("Demo 4: Network Access Control")
    print("=" * 60)

    pm = PermissionManager()
    pm.grant_permissions(
        "network-plugin",
        permissions={PluginPermission.NETWORK_HTTP},
    )

    sandbox = PluginSandbox(
        config=SandboxConfig(
            enabled=True,
            network_whitelist=["api.feishu.cn", "open.feishu.cn", "localhost"],
        ),
        permission_manager=pm,
    )

    # Test network access checks
    hosts = [
        "api.feishu.cn",
        "open.feishu.cn",
        "localhost",
        "malicious-site.com",
        "unknown-api.io",
    ]

    print("\nNetwork access checks:")
    for host in hosts:
        allowed = sandbox.check_network_access("network-plugin", host)
        status = "ALLOWED" if allowed else "DENIED"
        print(f"  {host}: {status}")

    # Check violations
    violations = sandbox.get_violations("network-plugin")
    print(f"\n  Violations recorded: {len(violations)}")


# =============================================================================
# Demo 5: System Access Control
# =============================================================================
def demo_system_access() -> None:
    """Demonstrate system access control."""
    print("\n" + "=" * 60)
    print("Demo 5: System Access Control")
    print("=" * 60)

    pm = PermissionManager()
    pm.grant_permissions(
        "system-plugin",
        permissions={PluginPermission.SYSTEM_INFO},
    )

    sandbox = PluginSandbox(
        config=SandboxConfig(enabled=True),
        permission_manager=pm,
    )

    # Test system access checks
    access_types = ["info", "exec", "env"]

    print("\nSystem access checks:")
    for access_type in access_types:
        allowed = sandbox.check_system_access("system-plugin", access_type)
        status = "ALLOWED" if allowed else "DENIED"
        print(f"  {access_type}: {status}")


# =============================================================================
# Demo 6: Violation Tracking
# =============================================================================
def demo_violation_tracking() -> None:
    """Demonstrate violation tracking."""
    print("\n" + "=" * 60)
    print("Demo 6: Violation Tracking")
    print("=" * 60)

    sandbox = PluginSandbox(config=SandboxConfig(enabled=True))

    # Record some violations
    sandbox.record_violation(
        "plugin-a",
        "file_access_denied",
        "Attempted to read /etc/passwd",
    )
    sandbox.record_violation(
        "plugin-a",
        "network_blocked",
        "Host malicious.com not in whitelist",
    )
    sandbox.record_violation(
        "plugin-b",
        "permission_denied",
        "Missing SYSTEM_EXEC permission",
    )

    print("\nRecorded violations:")

    # Get all violations
    all_violations = sandbox.get_violations()
    print(f"  Total violations: {len(all_violations)}")

    # Get violations for specific plugin
    plugin_a_violations = sandbox.get_violations("plugin-a")
    print(f"  Plugin-A violations: {len(plugin_a_violations)}")

    for v in plugin_a_violations:
        print(f"    - {v.violation_type}: {v.details}")

    # Convert to dict
    print("\n--- Violation as dictionary ---")
    v = plugin_a_violations[0]
    data = v.to_dict()
    print(f"  Plugin: {data['plugin_name']}")
    print(f"  Type: {data['violation_type']}")
    print(f"  Details: {data['details']}")

    # Clear violations
    sandbox.clear_violations("plugin-a")
    remaining = sandbox.get_violations()
    print(f"\n  After clearing plugin-a: {len(remaining)} violations remaining")


# =============================================================================
# Demo 7: Plugin Context
# =============================================================================
def demo_plugin_context() -> None:
    """Demonstrate plugin context usage."""
    print("\n" + "=" * 60)
    print("Demo 7: Plugin Context")
    print("=" * 60)

    pm = PermissionManager()
    pm.grant_permissions(
        "context-plugin",
        permissions={
            PluginPermission.FILE_READ,
            PluginPermission.FILE_WRITE,
            PluginPermission.SYSTEM_ENV,
        },
    )

    sandbox = PluginSandbox(
        config=SandboxConfig(
            enabled=True,
            allowed_paths=[tempfile.gettempdir()],
        ),
        permission_manager=pm,
    )

    context = sandbox.create_context("context-plugin")

    print("\nPlugin context operations:")

    # Check permissions through context
    print("\n--- Permission checks ---")
    print(f"  FILE_READ: {context.check_permission(PluginPermission.FILE_READ)}")
    print(f"  NETWORK_HTTP: {context.check_permission(PluginPermission.NETWORK_HTTP)}")

    # Read/write files through context
    print("\n--- File operations ---")
    test_file = Path(tempfile.gettempdir()) / "context_test.txt"

    try:
        context.write_file(test_file, "Hello from plugin context!")
        print(f"  Wrote to: {test_file}")

        content = context.read_file(test_file)
        print(f"  Read content: {content}")

        # Cleanup
        test_file.unlink()
    except PermissionError as e:
        print(f"  Permission error: {e}")

    # Get environment variable
    print("\n--- Environment access ---")
    path_value = context.get_env("PATH", "not found")
    print(f"  PATH: {path_value[:50]}...")

    # Get context stats
    print("\n--- Context stats ---")
    stats = context.get_stats()
    print(f"  Plugin: {stats['plugin_name']}")
    print(f"  Call count: {stats['call_count']}")
    print(f"  Execution time: {stats['total_execution_time']:.4f}s")
    print(f"  Uptime: {stats['uptime']:.2f}s")


# =============================================================================
# Demo 8: Function Wrapping
# =============================================================================
def demo_function_wrapping() -> None:
    """Demonstrate wrapping functions with sandbox protection."""
    print("\n" + "=" * 60)
    print("Demo 8: Function Wrapping")
    print("=" * 60)

    sandbox = PluginSandbox(config=SandboxConfig(enabled=True))
    context = sandbox.create_context("wrap-plugin")

    # Define a function to wrap
    def plugin_task(x: int, y: int) -> int:
        """A simple task that adds two numbers."""
        return x + y

    # Wrap the function
    wrapped_task = sandbox.wrap_function("wrap-plugin", plugin_task)

    print("\nExecuting wrapped function:")
    result = wrapped_task(10, 20)
    print(f"  Result: {result}")

    # Check stats after execution
    print(f"  Call count: {context.call_count}")
    print(f"  Execution time: {context.total_execution_time:.6f}s")

    # Execute multiple times
    for i in range(5):
        wrapped_task(i, i * 2)

    print("\n  After 5 more calls:")
    print(f"  Call count: {context.call_count}")
    print(f"  Total execution time: {context.total_execution_time:.6f}s")


# =============================================================================
# Demo 9: Global Sandbox
# =============================================================================
def demo_global_sandbox() -> None:
    """Demonstrate global sandbox configuration."""
    print("\n" + "=" * 60)
    print("Demo 9: Global Sandbox")
    print("=" * 60)

    # Configure global sandbox
    config = SandboxConfig(
        enabled=True,
        max_execution_time=120.0,
        network_whitelist=["*.feishu.cn"],
    )

    sandbox = configure_sandbox(config)
    print("\nGlobal sandbox configured:")
    print(f"  Max execution time: {sandbox.config.max_execution_time}s")

    # Get global sandbox (should be same instance)
    global_sandbox = get_sandbox()
    print(f"  Same instance: {sandbox is global_sandbox}")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all plugin sandbox demonstrations."""
    print("=" * 60)
    print("Plugin Sandbox System Examples")
    print("=" * 60)

    demos = [
        ("Sandbox Configuration", demo_sandbox_config),
        ("Creating a Sandbox", demo_create_sandbox),
        ("File Access Control", demo_file_access),
        ("Network Access Control", demo_network_access),
        ("System Access Control", demo_system_access),
        ("Violation Tracking", demo_violation_tracking),
        ("Plugin Context", demo_plugin_context),
        ("Function Wrapping", demo_function_wrapping),
        ("Global Sandbox", demo_global_sandbox),
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
