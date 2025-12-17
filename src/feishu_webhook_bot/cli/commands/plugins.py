"""CLI commands for plugin management."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..base import BotConfig, setup_logging


def cmd_plugins(args: argparse.Namespace) -> int:
    """Handle plugins command with subcommands.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    subcommand = getattr(args, "plugins_command", None)

    if subcommand is None or subcommand == "list":
        return _cmd_plugins_list(args)
    elif subcommand == "info":
        return _cmd_plugins_info(args)
    elif subcommand == "enable":
        return _cmd_plugins_enable(args)
    elif subcommand == "disable":
        return _cmd_plugins_disable(args)
    elif subcommand == "reload":
        return _cmd_plugins_reload(args)
    elif subcommand == "config":
        return _cmd_plugins_config(args)
    elif subcommand == "priority":
        return _cmd_plugins_priority(args)
    elif subcommand == "permissions":
        return _cmd_plugins_permissions(args)
    else:
        print(f"Unknown subcommand: {subcommand}")
        return 1


def _get_plugin_manager(config_path: str):
    """Create a plugin manager instance.

    Args:
        config_path: Path to configuration file

    Returns:
        Tuple of (config, plugin_manager) or (None, None) on error
    """
    from ...core.client import FeishuWebhookClient
    from ...plugins import PluginManager

    path = Path(config_path)
    if not path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return None, None

    try:
        config = BotConfig.from_yaml(path)
        # Store config path for later use
        config._config_path = str(path)

        # Create temporary client
        webhook = config.get_webhook("default") or config.webhooks[0]
        client = FeishuWebhookClient(webhook)

        manager = PluginManager(config, client, None)
        manager.load_plugins()

        return config, manager
    except Exception as e:
        print(f"Error loading plugins: {e}")
        return None, None


def _cmd_plugins_list(args: argparse.Namespace) -> int:
    """List all plugins."""
    setup_logging()
    console = Console()

    config_path = getattr(args, "config", "config.yaml")
    config, manager = _get_plugin_manager(config_path)

    if manager is None:
        return 1

    try:
        plugins = manager.get_all_plugin_info()

        if not plugins:
            console.print("[yellow]No plugins loaded.[/yellow]")
            console.print("\nTip: Create plugins in the 'plugins' directory.")
            return 0

        # Create table
        table = Table(title="Loaded Plugins", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Version", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Author", style="dim")
        table.add_column("Description")

        for plugin in plugins:
            status = "[green]●[/green] Loaded" if plugin.enabled else "[yellow]○[/yellow] Loaded"
            table.add_row(
                plugin.name,
                plugin.version,
                status,
                plugin.author or "-",
                (plugin.description[:50] + "...")
                if len(plugin.description) > 50
                else (plugin.description or "-"),
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(plugins)} plugins[/dim]")

        # Show disabled plugins from config
        disabled_in_config = []
        for setting in config.plugins.plugin_settings:
            if not setting.enabled and setting.plugin_name not in [p.name for p in plugins]:
                disabled_in_config.append(setting.plugin_name)

        if disabled_in_config:
            console.print(f"\n[yellow]Disabled in config: {', '.join(disabled_in_config)}[/yellow]")

        return 0

    except Exception as e:
        console.print(f"[red]Error listing plugins: {e}[/red]")
        return 1


def _cmd_plugins_info(args: argparse.Namespace) -> int:
    """Show detailed plugin information."""
    setup_logging()
    console = Console()

    plugin_name = getattr(args, "plugin_name", None)
    if not plugin_name:
        console.print("[red]Error: Plugin name required[/red]")
        return 1

    config_path = getattr(args, "config", "config.yaml")
    config, manager = _get_plugin_manager(config_path)

    if manager is None:
        return 1

    try:
        info = manager.get_plugin_info(plugin_name)

        if info is None:
            console.print(f"[red]Plugin not found: {plugin_name}[/red]")
            return 1

        # Build info panel
        desc = (info.description or "N/A")[:50]
        status = "[green]Enabled[/green]" if info.enabled else "[yellow]Disabled[/yellow]"
        has_schema = "Yes" if info.has_schema else "No"
        info_text = f"""[bold cyan]Name:[/bold cyan] {info.name}
[bold cyan]Version:[/bold cyan] {info.version}
[bold cyan]Author:[/bold cyan] {info.author or "Unknown"}
[bold cyan]Desc:[/bold cyan] {desc}
[bold cyan]Status:[/bold cyan] {status}
[bold cyan]File:[/bold cyan] {info.file_path}
[bold cyan]Has Schema:[/bold cyan] {has_schema}
[bold cyan]Registered Jobs:[/bold cyan] {len(info.jobs)}"""

        console.print(Panel(info_text, title=f"Plugin: {plugin_name}", border_style="blue"))

        # Show configuration
        if info.config:
            console.print("\n[bold]Current Configuration:[/bold]")
            for key, value in info.config.items():
                # Mask sensitive values
                display_value = "***" if "secret" in key.lower() or "key" in key.lower() else value
                console.print(f"  [cyan]{key}:[/cyan] {display_value}")

        # Show schema if available
        schema = manager.get_plugin_schema(plugin_name)
        if schema:
            console.print("\n[bold]Configuration Schema:[/bold]")
            schema_table = Table(show_header=True, header_style="bold")
            schema_table.add_column("Field", style="green")
            schema_table.add_column("Type", style="blue")
            schema_table.add_column("Required", style="yellow")
            schema_table.add_column("Default")
            schema_table.add_column("Description")

            for field_name, field_info in schema.items():
                schema_table.add_row(
                    field_name,
                    field_info.get("type", "string"),
                    "Yes" if field_info.get("required") else "No",
                    str(field_info.get("default", "-")),
                    field_info.get("description", "-")[:40],
                )

            console.print(schema_table)

        # Show jobs
        if info.jobs:
            console.print("\n[bold]Registered Jobs:[/bold]")
            for job_id in info.jobs:
                console.print(f"  • {job_id}")

        return 0

    except Exception as e:
        console.print(f"[red]Error getting plugin info: {e}[/red]")
        return 1


def _cmd_plugins_enable(args: argparse.Namespace) -> int:
    """Enable a plugin."""
    setup_logging()
    console = Console()

    plugin_name = getattr(args, "plugin_name", None)
    if not plugin_name:
        console.print("[red]Error: Plugin name required[/red]")
        return 1

    config_path = getattr(args, "config", "config.yaml")
    config, manager = _get_plugin_manager(config_path)

    if manager is None:
        return 1

    try:
        # Check if plugin exists
        if plugin_name not in manager.plugins:
            console.print(f"[red]Plugin not found: {plugin_name}[/red]")
            return 1

        # Enable plugin
        if manager.enable_plugin(plugin_name):
            console.print(f"[green]✓ Plugin enabled: {plugin_name}[/green]")

            # Update config file if requested
            if getattr(args, "save", False):
                if manager.set_plugin_enabled_in_config(plugin_name, True):
                    console.print("[dim]Configuration file updated[/dim]")
                else:
                    console.print("[yellow]Warning: Failed to update config file[/yellow]")

            return 0
        else:
            console.print(f"[red]Failed to enable plugin: {plugin_name}[/red]")
            return 1

    except Exception as e:
        console.print(f"[red]Error enabling plugin: {e}[/red]")
        return 1


def _cmd_plugins_disable(args: argparse.Namespace) -> int:
    """Disable a plugin."""
    setup_logging()
    console = Console()

    plugin_name = getattr(args, "plugin_name", None)
    if not plugin_name:
        console.print("[red]Error: Plugin name required[/red]")
        return 1

    config_path = getattr(args, "config", "config.yaml")
    config, manager = _get_plugin_manager(config_path)

    if manager is None:
        return 1

    try:
        # Check if plugin exists
        if plugin_name not in manager.plugins:
            console.print(f"[red]Plugin not found: {plugin_name}[/red]")
            return 1

        # Disable plugin
        if manager.disable_plugin(plugin_name):
            console.print(f"[green]✓ Plugin disabled: {plugin_name}[/green]")

            # Update config file if requested
            if getattr(args, "save", False):
                if manager.set_plugin_enabled_in_config(plugin_name, False):
                    console.print("[dim]Configuration file updated[/dim]")
                else:
                    console.print("[yellow]Warning: Failed to update config file[/yellow]")

            return 0
        else:
            console.print(f"[red]Failed to disable plugin: {plugin_name}[/red]")
            return 1

    except Exception as e:
        console.print(f"[red]Error disabling plugin: {e}[/red]")
        return 1


def _cmd_plugins_reload(args: argparse.Namespace) -> int:
    """Reload plugin(s)."""
    setup_logging()
    console = Console()

    plugin_name = getattr(args, "plugin_name", None)
    config_path = getattr(args, "config", "config.yaml")
    config, manager = _get_plugin_manager(config_path)

    if manager is None:
        return 1

    try:
        if plugin_name:
            # Reload specific plugin
            if plugin_name not in manager.plugins:
                console.print(f"[red]Plugin not found: {plugin_name}[/red]")
                return 1

            if manager.reload_plugin(plugin_name):
                console.print(f"[green]✓ Plugin reloaded: {plugin_name}[/green]")
                return 0
            else:
                console.print(f"[red]Failed to reload plugin: {plugin_name}[/red]")
                return 1
        else:
            # Reload all plugins
            console.print("[yellow]Reloading all plugins...[/yellow]")
            manager.reload_plugins()
            console.print(f"[green]✓ Reloaded {len(manager.plugins)} plugins[/green]")
            return 0

    except Exception as e:
        console.print(f"[red]Error reloading plugins: {e}[/red]")
        return 1


def _cmd_plugins_config(args: argparse.Namespace) -> int:
    """View or update plugin configuration."""
    setup_logging()
    console = Console()

    plugin_name = getattr(args, "plugin_name", None)
    if not plugin_name:
        console.print("[red]Error: Plugin name required[/red]")
        return 1

    config_path = getattr(args, "config", "config.yaml")
    config, manager = _get_plugin_manager(config_path)

    if manager is None:
        return 1

    try:
        # Check if plugin exists
        if plugin_name not in manager.plugins:
            console.print(f"[red]Plugin not found: {plugin_name}[/red]")
            return 1

        # Handle --set option
        set_values = getattr(args, "set", None)
        if set_values:
            new_config = {}
            for item in set_values:
                if "=" not in item:
                    console.print(f"[red]Invalid format: {item}. Use key=value[/red]")
                    return 1
                key, value = item.split("=", 1)

                # Try to parse value as JSON for complex types
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    parsed_value = value

                new_config[key] = parsed_value

            # Update configuration
            reload_after = getattr(args, "reload", False)
            success, errors = manager.update_plugin_config(
                plugin_name,
                new_config,
                save_to_file=True,
                reload_plugin=reload_after,
            )

            if success:
                console.print(f"[green]✓ Configuration updated for: {plugin_name}[/green]")
                for key, value in new_config.items():
                    console.print(f"  [cyan]{key}:[/cyan] {value}")
                if reload_after:
                    console.print("[dim]Plugin reloaded[/dim]")
                return 0
            else:
                console.print("[red]Failed to update configuration:[/red]")
                for error in errors:
                    console.print(f"  • {error}")
                return 1

        # Handle --get option
        get_key = getattr(args, "get", None)
        if get_key:
            current_config = manager.get_plugin_config(plugin_name)
            if get_key in current_config:
                value = current_config[get_key]
                # Mask sensitive values
                if "secret" in get_key.lower() or "key" in get_key.lower():
                    console.print(f"[cyan]{get_key}:[/cyan] ***")
                else:
                    console.print(f"[cyan]{get_key}:[/cyan] {value}")
            else:
                console.print(f"[yellow]Key not found: {get_key}[/yellow]")
            return 0

        # Default: show all configuration
        current_config = manager.get_plugin_config(plugin_name)

        if not current_config:
            console.print(f"[yellow]No configuration for plugin: {plugin_name}[/yellow]")

            # Show schema if available
            schema = manager.get_plugin_schema(plugin_name)
            if schema:
                console.print("\n[bold]Available configuration options:[/bold]")
                for field_name, field_info in schema.items():
                    required = "[red]*[/red]" if field_info.get("required") else ""
                    default_val = field_info.get("default")
                    default = f" (default: {default_val})" if default_val else ""
                    desc = field_info.get("description", "")
                    console.print(f"  [cyan]{field_name}[/cyan]{required}: {desc}{default}")
            return 0

        console.print(f"[bold]Configuration for {plugin_name}:[/bold]\n")
        for key, value in current_config.items():
            # Mask sensitive values
            if "secret" in key.lower() or "key" in key.lower():
                console.print(f"  [cyan]{key}:[/cyan] ***")
            else:
                console.print(f"  [cyan]{key}:[/cyan] {value}")

        # Show hint for setting values
        console.print("\n[dim]To set a value: plugins config <name> --set key=value[/dim]")

        return 0

    except Exception as e:
        console.print(f"[red]Error managing plugin config: {e}[/red]")
        return 1


def _cmd_plugins_priority(args: argparse.Namespace) -> int:
    """Set plugin loading priority."""
    setup_logging()
    console = Console()

    plugin_name = getattr(args, "plugin_name", None)
    priority = getattr(args, "priority", None)

    if not plugin_name or priority is None:
        console.print("[red]Error: Plugin name and priority required[/red]")
        return 1

    config_path = getattr(args, "config", "config.yaml")

    try:
        from ...plugins.config_updater import ConfigUpdater

        path = Path(config_path)
        if not path.exists():
            console.print(f"[red]Error: Configuration file not found: {config_path}[/red]")
            return 1

        updater = ConfigUpdater(config_path)

        # Load current config
        config = updater._load_config()
        updater._ensure_plugins_section(config)

        # Find or create plugin entry
        plugin_entry = updater._find_plugin_entry(config["plugins"]["plugin_settings"], plugin_name)

        if plugin_entry is None:
            plugin_entry = {
                "plugin_name": plugin_name,
                "enabled": True,
                "settings": {},
                "priority": priority,
            }
            config["plugins"]["plugin_settings"].append(plugin_entry)
        else:
            plugin_entry["priority"] = priority

        updater._save_config(config)
        console.print(f"[green]✓ Set priority for {plugin_name} to {priority}[/green]")
        console.print("[dim]Lower values load first. Restart bot to apply.[/dim]")
        return 0

    except Exception as e:
        console.print(f"[red]Error setting priority: {e}[/red]")
        return 1


def _cmd_plugins_permissions(args: argparse.Namespace) -> int:
    """View or manage plugin permissions."""
    setup_logging()
    console = Console()

    plugin_name = getattr(args, "plugin_name", None)
    grant_perm = getattr(args, "grant", None)
    revoke_perm = getattr(args, "revoke", None)
    approve_perm = getattr(args, "approve", None)
    config_path = getattr(args, "config", "config.yaml")

    try:
        _, manager = _get_plugin_manager(config_path)
        if not manager:
            console.print("[red]Error: Failed to initialize plugin manager[/red]")
            return 1

        # If no plugin specified, list all permissions
        if not plugin_name:
            from ...plugins.permissions import PluginPermission

            console.print("\n[bold]Available Permissions:[/bold]\n")
            table = Table(show_header=True)
            table.add_column("Permission", style="cyan")
            table.add_column("Category", style="yellow")
            table.add_column("Dangerous", style="red")

            from ...plugins.permissions import DANGEROUS_PERMISSIONS

            for perm in PluginPermission:
                category = perm.name.split("_")[0]
                is_dangerous = "⚠️ Yes" if perm in DANGEROUS_PERMISSIONS else "No"
                table.add_row(perm.name, category, is_dangerous)

            console.print(table)
            return 0

        # Get plugin
        plugin = manager.plugins.get(plugin_name)
        if not plugin:
            console.print(f"[red]Error: Plugin not found: {plugin_name}[/red]")
            return 1

        # Handle grant/revoke/approve
        if grant_perm:
            if manager.grant_plugin_permission(plugin_name, grant_perm):
                console.print(f"[green]✓ Granted {grant_perm} to {plugin_name}[/green]")
            else:
                console.print(f"[red]Failed to grant {grant_perm}[/red]")
            return 0

        if revoke_perm:
            if manager.revoke_plugin_permission(plugin_name, revoke_perm):
                console.print(f"[yellow]✓ Revoked {revoke_perm} from {plugin_name}[/yellow]")
            else:
                console.print(f"[red]Failed to revoke {revoke_perm}[/red]")
            return 0

        if approve_perm:
            if manager.approve_dangerous_permission(plugin_name, approve_perm):
                console.print(f"[green]✓ Approved dangerous permission {approve_perm}[/green]")
            else:
                console.print(f"[red]Failed to approve {approve_perm}[/red]")
            return 0

        # Show plugin permissions
        perm_info = manager.get_plugin_permissions(plugin_name)

        console.print(
            Panel(
                f"[bold]Plugin:[/bold] {plugin_name}",
                title="Permission Status",
            )
        )

        # Required permissions
        console.print("\n[bold cyan]Required Permissions:[/bold cyan]")
        if perm_info.get("required"):
            for p in perm_info["required"]:
                console.print(f"  • {p}")
        else:
            console.print("  [dim]None declared[/dim]")

        # Granted permissions
        console.print("\n[bold green]Granted Permissions:[/bold green]")
        if perm_info.get("granted"):
            for p in perm_info["granted"]:
                console.print(f"  ✓ {p}")
        else:
            console.print("  [dim]None[/dim]")

        # Denied permissions
        if perm_info.get("denied"):
            console.print("\n[bold red]Denied Permissions:[/bold red]")
            for p in perm_info["denied"]:
                console.print(f"  ✗ {p}")

        # Pending dangerous approvals
        if perm_info.get("pending_dangerous"):
            console.print("\n[bold yellow]⚠️ Pending Dangerous Approvals:[/bold yellow]")
            for p in perm_info["pending_dangerous"]:
                console.print(f"  ⚠ {p}")
            console.print("\n[dim]Use --approve <PERMISSION> to approve[/dim]")

        # Overall status
        all_granted = perm_info.get("all_granted", True)
        if all_granted:
            status = "[green]✓ All permissions granted[/green]"
        else:
            status = "[yellow]⚠ Some permissions missing[/yellow]"
        console.print(f"\n[bold]Status:[/bold] {status}")

        return 0

    except Exception as e:
        console.print(f"[red]Error managing permissions: {e}[/red]")
        return 1


__all__ = ["cmd_plugins"]
