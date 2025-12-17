"""Chat CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..base import BotConfig, logger


def cmd_chat(args: argparse.Namespace) -> int:
    """Handle chat system commands."""
    if not args.chat_command:
        print("Usage: feishu-webhook-bot chat <subcommand>")
        print("Subcommands: config, test, commands, broadcast")
        return 1

    handlers = {
        "config": _cmd_chat_config,
        "test": _cmd_chat_test,
        "commands": _cmd_chat_commands,
        "broadcast": _cmd_chat_broadcast,
    }

    handler = handlers.get(args.chat_command)
    if handler:
        return handler(args)

    print(f"Unknown chat subcommand: {args.chat_command}")
    return 1


def _cmd_chat_config(args: argparse.Namespace) -> int:
    """Handle chat config command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Chat Configuration[/]\n")

        # Show webhook/provider configuration
        if config.webhooks:
            console.print(f"[bold]Webhooks:[/] {len(config.webhooks)}")
            for wh in config.webhooks:
                console.print(f"  - {wh.name}")

        if config.providers:
            console.print(f"\n[bold]Providers:[/] {len(config.providers)}")
            for p in config.providers:
                console.print(f"  - {p.name} ({p.provider_type})")

        # Show AI chat configuration
        if config.ai and config.ai.enabled:
            console.print("\n[bold]AI Chat:[/] Enabled")
            console.print(f"  Model: {config.ai.model or 'Not set'}")
        else:
            console.print("\n[bold]AI Chat:[/] Disabled")

        return 0

    except Exception as e:
        logger.error(f"Error getting chat config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_chat_test(args: argparse.Namespace) -> int:
    """Handle chat test command."""
    console = Console()

    console.print("\n[bold]Testing Chat Message[/]\n")
    console.print(f"Platform: {args.platform}")
    console.print(f"Message: {args.message}")

    console.print("\n[yellow]Simulated processing:[/]")

    # Check if it's a command
    if args.message.startswith("/"):
        console.print(f"  [cyan]Detected command:[/] {args.message}")
        console.print("  Command would be handled by CommandHandler")
    else:
        console.print(f"  [cyan]Regular message:[/] {args.message}")
        console.print("  Message would be processed by ChatController")

    console.print("\n[yellow]Note: Full message processing requires bot runtime context.[/]")

    return 0


def _cmd_chat_commands(args: argparse.Namespace) -> int:
    """Handle chat commands listing."""
    console = Console()

    console.print("\n[bold]Built-in Chat Commands[/]\n")

    # List built-in commands from CommandHandler
    commands = {
        "/help": "显示帮助信息",
        "/reset": "重置当前对话，清除上下文",
        "/history": "显示对话历史摘要",
        "/model": "切换AI模型 (用法: /model gpt-4o)",
        "/stats": "显示使用统计",
        "/clear": "清除当前会话的上下文",
    }

    table = Table(title="Built-in Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")

    for cmd, desc in commands.items():
        table.add_row(cmd, desc)

    console.print(table)
    console.print("\n[dim]Custom commands can be registered via plugins.[/]")

    return 0


def _cmd_chat_broadcast(args: argparse.Namespace) -> int:
    """Handle chat broadcast command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Broadcasting Message[/]\n")
        console.print(f"Message: {args.message}")

        targets = []
        if config.webhooks:
            targets.extend([f"webhook:{wh.name}" for wh in config.webhooks])
        if config.providers:
            targets.extend([f"provider:{p.name}" for p in config.providers])

        if targets:
            console.print(f"\n[bold]Targets ({len(targets)}):[/]")
            for t in targets:
                console.print(f"  - {t}")
        else:
            console.print("\n[yellow]No targets configured.[/]")

        console.print("\n[yellow]Note: Broadcasting requires bot runtime context.[/]")
        console.print("Start the bot to send messages to all configured targets.")

        return 0

    except Exception as e:
        logger.error(f"Error in broadcast: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_chat"]
