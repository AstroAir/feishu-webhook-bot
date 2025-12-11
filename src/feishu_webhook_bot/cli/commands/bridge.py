"""Bridge CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..base import BotConfig, logger


def cmd_bridge(args: argparse.Namespace) -> int:
    """Handle bridge management commands.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    if not args.bridge_command:
        print("Usage: feishu-webhook-bot bridge <subcommand>")
        print("Subcommands: status, list, enable, disable, test")
        return 1

    handlers = {
        "status": _cmd_bridge_status,
        "list": _cmd_bridge_list,
        "enable": _cmd_bridge_enable,
        "disable": _cmd_bridge_disable,
        "test": _cmd_bridge_test,
    }

    handler = handlers.get(args.bridge_command)
    if handler:
        return handler(args)

    print(f"Unknown bridge subcommand: {args.bridge_command}")
    return 1


def _cmd_bridge_status(args: argparse.Namespace) -> int:
    """Handle bridge status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        bridge_cfg = config.message_bridge
        if not bridge_cfg:
            console.print("[yellow]Message bridge not configured.[/]")
            return 0

        status = "[green]Enabled[/]" if bridge_cfg.enabled else "[red]Disabled[/]"
        rules_count = len(bridge_cfg.rules)
        enabled_rules = sum(1 for r in bridge_cfg.rules if r.enabled)

        info_lines = [
            f"[bold]Status:[/] {status}",
            f"[bold]Total Rules:[/] {rules_count}",
            f"[bold]Enabled Rules:[/] {enabled_rules}",
            f"[bold]Rate Limit:[/] {bridge_cfg.rate_limit_per_minute}/min",
            f"[bold]Retry on Failure:[/] {bridge_cfg.retry_on_failure}",
            f"[bold]Max Retries:[/] {bridge_cfg.max_retries}",
            f"[bold]Default Format:[/] {bridge_cfg.default_format}",
        ]

        console.print(Panel("\n".join(info_lines), title="Message Bridge Status"))
        return 0

    except Exception as e:
        logger.error(f"Error getting bridge status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_bridge_list(args: argparse.Namespace) -> int:
    """Handle bridge list command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        bridge_cfg = config.message_bridge
        if not bridge_cfg or not bridge_cfg.rules:
            console.print("[yellow]No bridge rules configured.[/]")
            return 0

        table = Table(title="Bridge Rules")
        table.add_column("Name", style="cyan")
        table.add_column("Status")
        table.add_column("Source")
        table.add_column("Target")
        table.add_column("Chat Type")

        for rule in bridge_cfg.rules:
            status = "[green]Enabled[/]" if rule.enabled else "[red]Disabled[/]"
            table.add_row(
                rule.name,
                status,
                rule.source_provider,
                f"{rule.target_provider}:{rule.target_chat_id}",
                rule.source_chat_type,
            )

        console.print(table)
        return 0

    except Exception as e:
        logger.error(f"Error listing bridge rules: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_bridge_enable(args: argparse.Namespace) -> int:
    """Handle bridge enable command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        bridge_cfg = config.message_bridge
        if not bridge_cfg:
            console.print("[red]Message bridge not configured.[/]")
            return 1

        for rule in bridge_cfg.rules:
            if rule.name == args.rule_name:
                if rule.enabled:
                    console.print(
                        f"[yellow]Rule '{args.rule_name}' is already enabled.[/]"
                    )
                else:
                    console.print(
                        f"[green]Rule '{args.rule_name}' would be enabled.[/]"
                    )
                    console.print("[dim]Note: Changes require config file update.[/]")
                return 0

        console.print(f"[red]Rule not found: {args.rule_name}[/]")
        return 1

    except Exception as e:
        logger.error(f"Error enabling bridge rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_bridge_disable(args: argparse.Namespace) -> int:
    """Handle bridge disable command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        bridge_cfg = config.message_bridge
        if not bridge_cfg:
            console.print("[red]Message bridge not configured.[/]")
            return 1

        for rule in bridge_cfg.rules:
            if rule.name == args.rule_name:
                if not rule.enabled:
                    console.print(
                        f"[yellow]Rule '{args.rule_name}' is already disabled.[/]"
                    )
                else:
                    console.print(
                        f"[green]Rule '{args.rule_name}' would be disabled.[/]"
                    )
                    console.print("[dim]Note: Changes require config file update.[/]")
                return 0

        console.print(f"[red]Rule not found: {args.rule_name}[/]")
        return 1

    except Exception as e:
        logger.error(f"Error disabling bridge rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_bridge_test(args: argparse.Namespace) -> int:
    """Handle bridge test command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        bridge_cfg = config.message_bridge
        if not bridge_cfg:
            console.print("[red]Message bridge not configured.[/]")
            return 1

        rule = None
        for r in bridge_cfg.rules:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            console.print(f"[red]Rule not found: {args.rule_name}[/]")
            return 1

        # Show what would happen with this rule
        test_msg = args.message
        format_template = bridge_cfg.default_format

        transformed = format_template.format(
            source="TestPlatform",
            sender="TestUser",
            content=test_msg,
            time="12:00:00",
        )

        if rule.message_prefix:
            transformed = rule.message_prefix + transformed
        if rule.message_suffix:
            transformed = transformed + rule.message_suffix

        info_lines = [
            f"[bold]Rule:[/] {rule.name}",
            f"[bold]Status:[/] {'Enabled' if rule.enabled else 'Disabled'}",
            f"[bold]Source:[/] {rule.source_provider} ({rule.source_chat_type})",
            f"[bold]Target:[/] {rule.target_provider}:{rule.target_chat_id}",
            "",
            "[bold]Original Message:[/]",
            f"  {test_msg}",
            "",
            "[bold]Transformed Message:[/]",
            f"  {transformed}",
        ]

        console.print(Panel("\n".join(info_lines), title="Bridge Rule Test"))
        console.print("\n[yellow]Note: This is a dry run. No message was sent.[/]")
        return 0

    except Exception as e:
        logger.error(f"Error testing bridge rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_bridge"]
