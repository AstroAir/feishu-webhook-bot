"""Automation CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..base import BotConfig, logger


def cmd_automation(args: argparse.Namespace) -> int:
    """Handle automation management commands.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    if not args.automation_command:
        print("Usage: feishu-webhook-bot automation <subcommand>")
        print("Subcommands: list, status, trigger, test, enable, disable, history, details")
        return 1

    handlers = {
        "list": _cmd_automation_list,
        "status": _cmd_automation_status,
        "trigger": _cmd_automation_trigger,
        "test": _cmd_automation_test,
        "enable": _cmd_automation_enable,
        "disable": _cmd_automation_disable,
        "history": _cmd_automation_history,
        "details": _cmd_automation_details,
    }

    handler = handlers.get(args.automation_command)
    if handler:
        return handler(args)

    print(f"Unknown automation subcommand: {args.automation_command}")
    return 1


def _cmd_automation_list(args: argparse.Namespace) -> int:
    """Handle automation list command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.automations:
            console.print("[yellow]No automation rules configured.[/]")
            return 0

        table = Table(title="Automation Rules")
        table.add_column("Name", style="cyan")
        table.add_column("Trigger Type", style="magenta")
        table.add_column("Status")
        table.add_column("Actions", style="green")

        for rule in config.automations:
            trigger_type = rule.trigger.type if rule.trigger else "unknown"
            status = "[green]Enabled[/]" if rule.enabled else "[red]Disabled[/]"
            action_count = len(rule.actions) if rule.actions else 0

            table.add_row(
                rule.name,
                trigger_type,
                status,
                str(action_count),
            )

        console.print(table)
        return 0

    except Exception as e:
        logger.error(f"Error listing automation rules: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_status(args: argparse.Namespace) -> int:
    """Handle automation status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        enabled_count = sum(1 for r in config.automations if r.enabled)
        disabled_count = len(config.automations) - enabled_count

        info = f"""
[bold]Automation Engine Status[/]

[bold]Total Rules:[/] {len(config.automations)}
[bold]Enabled:[/] [green]{enabled_count}[/]
[bold]Disabled:[/] [red]{disabled_count}[/]
"""

        console.print(info)
        return 0

    except Exception as e:
        logger.error(f"Error getting automation status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_trigger(args: argparse.Namespace) -> int:
    """Handle automation trigger command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            print(f"Automation rule not found: {args.rule_name}")
            return 1

        print(f"Triggering automation rule: {args.rule_name}")
        print(f"  Trigger Type: {rule.trigger.type}")
        print(f"  Status: {'Enabled' if rule.enabled else 'Disabled'}")
        print(f"  Actions: {len(rule.actions)}")
        print("\nNote: Manual trigger simulation would require full bot context.")
        print("Please restart the bot to enable the rule if it's disabled.")

        return 0

    except Exception as e:
        logger.error(f"Error triggering automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_test(args: argparse.Namespace) -> int:
    """Handle automation test command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            print(f"Automation rule not found: {args.rule_name}")
            return 1

        console = Console()
        console.print(f"\n[bold]Testing Automation Rule: {args.rule_name}[/]\n")

        # Display rule configuration
        info_lines = [
            f"[bold]Name:[/] {rule.name}",
            f"[bold]Trigger Type:[/] {rule.trigger.type}",
            f"[bold]Enabled:[/] {rule.enabled}",
            f"[bold]Actions:[/] {len(rule.actions)}",
        ]

        if rule.default_webhooks:
            info_lines.append(
                f"[bold]Default Webhooks:[/] {', '.join(rule.default_webhooks)}"
            )

        for i, action in enumerate(rule.actions, 1):
            info_lines.append(f"  [green]Action {i}:[/] {action.type}")

        console.print("\n".join(info_lines))
        console.print(
            "\n[yellow]Note: Full test execution requires bot runtime context.[/]"
        )

        return 0

    except Exception as e:
        logger.error(f"Error testing automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_enable(args: argparse.Namespace) -> int:
    """Handle automation enable command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            print(f"Automation rule not found: {args.rule_name}")
            return 1

        if rule.enabled:
            print(f"Automation rule already enabled: {args.rule_name}")
            return 0

        rule.enabled = True
        config.save_yaml(config_path)

        print(f"Enabled automation rule: {args.rule_name}")
        return 0

    except Exception as e:
        logger.error(f"Error enabling automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_disable(args: argparse.Namespace) -> int:
    """Handle automation disable command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            print(f"Automation rule not found: {args.rule_name}")
            return 1

        if not rule.enabled:
            print(f"Automation rule already disabled: {args.rule_name}")
            return 0

        rule.enabled = False
        config.save_yaml(config_path)

        print(f"Disabled automation rule: {args.rule_name}")
        return 0

    except Exception as e:
        logger.error(f"Error disabling automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_history(args: argparse.Namespace) -> int:
    """Handle automation history command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            console.print(f"[red]Automation rule not found: {args.rule_name}[/]")
            return 1

        console.print(
            f"\n[bold]Automation Execution History: {args.rule_name}[/]\n"
        )
        console.print(f"Limit: {args.limit} entries")
        console.print("\n[yellow]Note: Execution history is tracked at runtime.[/]")
        console.print("Start the bot to begin tracking automation executions.")

        return 0

    except Exception as e:
        logger.error(f"Error getting automation history: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_details(args: argparse.Namespace) -> int:
    """Handle automation details command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            console.print(f"[red]Automation rule not found: {args.rule_name}[/]")
            return 1

        # Build details
        info_lines = [
            f"[bold]Name:[/] {rule.name}",
            f"[bold]Description:[/] {rule.description or 'N/A'}",
            f"[bold]Enabled:[/] {rule.enabled}",
        ]

        # Trigger info
        if rule.trigger:
            info_lines.append(f"[bold]Trigger Type:[/] {rule.trigger.type}")
            if rule.trigger.type == "schedule" and rule.trigger.schedule:
                info_lines.append(f"[bold]Schedule:[/] {rule.trigger.schedule}")
            elif rule.trigger.type == "event" and rule.trigger.event:
                info_lines.append(f"[bold]Event:[/] {rule.trigger.event}")

        info_lines.append(
            f"[bold]Actions:[/] {len(rule.actions) if rule.actions else 0}"
        )

        if rule.default_webhooks:
            info_lines.append(
                f"[bold]Default Webhooks:[/] {', '.join(rule.default_webhooks)}"
            )

        # Actions details
        if rule.actions:
            info_lines.append("\n[bold]Actions:[/]")
            for i, action in enumerate(rule.actions, 1):
                action_type = action.type if hasattr(action, 'type') else 'unknown'
                info_lines.append(f"  {i}. {action_type}")

        console.print(
            Panel("\n".join(info_lines), title=f"Automation Details: {args.rule_name}")
        )
        return 0

    except Exception as e:
        logger.error(f"Error getting automation details: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_automation"]
