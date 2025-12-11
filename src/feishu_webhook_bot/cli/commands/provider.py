"""Provider CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..base import BotConfig, logger


def cmd_provider(args: argparse.Namespace) -> int:
    """Handle provider management commands.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    if not args.provider_command:
        print("Usage: feishu-webhook-bot provider <subcommand>")
        print("Subcommands: list, info, test, stats")
        return 1

    handlers = {
        "list": _cmd_provider_list,
        "info": _cmd_provider_info,
        "test": _cmd_provider_test,
        "stats": _cmd_provider_stats,
        "send": _cmd_provider_send,
        "status": _cmd_provider_status,
    }

    handler = handlers.get(args.provider_command)
    if handler:
        return handler(args)

    print(f"Unknown provider subcommand: {args.provider_command}")
    return 1


def _cmd_provider_list(args: argparse.Namespace) -> int:
    """Handle provider list command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.providers:
            console.print("[yellow]No providers configured.[/]")
            return 0

        table = Table(title="Configured Providers")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status")
        table.add_column("Timeout (s)")

        for provider_config in config.providers:
            status = (
                "[green]Enabled[/]" if provider_config.enabled else "[red]Disabled[/]"
            )
            timeout = str(provider_config.timeout) if provider_config.timeout else "-"

            table.add_row(
                provider_config.name,
                provider_config.provider_type,
                status,
                timeout,
            )

        console.print(table)
        return 0

    except Exception as e:
        logger.error(f"Error listing providers: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_provider_info(args: argparse.Namespace) -> int:
    """Handle provider info command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        provider_config = None
        for p in config.providers:
            if p.name == args.provider_name:
                provider_config = p
                break

        if not provider_config:
            print(f"Provider not found: {args.provider_name}")
            return 1

        info_lines = [
            f"[bold]Name:[/] {provider_config.name}",
            f"[bold]Type:[/] {provider_config.provider_type}",
            f"[bold]Enabled:[/] {provider_config.enabled}",
        ]

        if provider_config.timeout:
            info_lines.append(f"[bold]Timeout:[/] {provider_config.timeout}s")

        if provider_config.retry:
            info_lines.append(
                f"[bold]Retry Max Attempts:[/] {provider_config.retry.max_attempts}"
            )
            info_lines.append(
                f"[bold]Retry Backoff:[/] {provider_config.retry.backoff_multiplier}x"
            )

        # Show provider-specific config
        provider_dict = provider_config.model_dump(
            exclude={'provider_type', 'name', 'enabled', 'timeout', 'retry'}
        )
        if provider_dict:
            info_lines.append("\n[bold]Configuration:[/]")
            for key, value in provider_dict.items():
                if key not in ['url', 'secret'] and not key.startswith('_'):
                    info_lines.append(f"  {key}: {value}")
                elif key == 'url':
                    # Mask URL for privacy
                    masked = value[:20] + "..." if len(str(value)) > 20 else value
                    info_lines.append(f"  {key}: {masked}")

        console.print(
            Panel("\n".join(info_lines), title=f"Provider: {args.provider_name}")
        )
        return 0

    except Exception as e:
        logger.error(f"Error getting provider info: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_provider_test(args: argparse.Namespace) -> int:
    """Handle provider test command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        provider_config = None
        for p in config.providers:
            if p.name == args.provider_name:
                provider_config = p
                break

        if not provider_config:
            print(f"Provider not found: {args.provider_name}")
            return 1

        console = Console()
        console.print(f"\n[bold]Testing Provider: {args.provider_name}[/]\n")

        console.print(f"Provider Type: [cyan]{provider_config.provider_type}[/]")
        console.print(f"Provider Name: [cyan]{provider_config.name}[/]")
        console.print(
            f"Status: {'[green]Enabled[/]' if provider_config.enabled else '[red]Disabled[/]'}"
        )

        if not provider_config.enabled:
            console.print("\n[yellow]Provider is disabled. Enable it to test.[/]")
            return 0

        console.print(
            "\n[yellow]Note: Full connectivity test requires bot runtime context.[/]"
        )
        console.print("Please start the bot to verify provider connectivity.")

        return 0

    except Exception as e:
        logger.error(f"Error testing provider: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_provider_stats(args: argparse.Namespace) -> int:
    """Handle provider stats command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        provider_config = None
        for p in config.providers:
            if p.name == args.provider_name:
                provider_config = p
                break

        if not provider_config:
            print(f"Provider not found: {args.provider_name}")
            return 1

        console = Console()
        console.print(f"\n[bold]Provider Statistics: {args.provider_name}[/]\n")

        console.print(
            "[yellow]Note: Provider statistics require bot runtime context.[/]"
        )
        console.print("Stats are tracked during message sending operations.")
        console.print("Please refer to message tracker for delivery statistics.")

        return 0

    except Exception as e:
        logger.error(f"Error getting provider stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_provider_send(args: argparse.Namespace) -> int:
    """Handle provider send command - send a message via a specific provider."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        # Find provider config
        provider_config = None
        for p in config.providers:
            if p.name == args.provider_name:
                provider_config = p
                break

        if not provider_config:
            print(f"Provider not found: {args.provider_name}")
            return 1

        if not provider_config.enabled:
            print(f"Provider '{args.provider_name}' is disabled")
            return 1

        console.print(f"\n[bold]Sending message via: {args.provider_name}[/]")
        console.print(f"Target: [cyan]{args.target}[/]")
        msg_preview = (
            args.message[:50] + "..." if len(args.message) > 50 else args.message
        )
        console.print(f"Message: [dim]{msg_preview}[/]")

        # Create provider instance and send
        if provider_config.provider_type == "feishu":
            from ...providers.feishu import FeishuProvider, FeishuProviderConfig

            feishu_cfg = FeishuProviderConfig(
                provider_type="feishu",
                name=provider_config.name,
                url=provider_config.webhook_url or "",
                secret=provider_config.secret,
                timeout=provider_config.timeout or config.http.timeout,
                retry=provider_config.retry or config.http.retry,
            )
            provider = FeishuProvider(feishu_cfg)
            provider.connect()
            try:
                result = provider.send_text(args.message, args.target)
                if result.success:
                    console.print("\n[green]✓ Message sent successfully![/]")
                    console.print(f"Message ID: {result.message_id}")
                else:
                    console.print(
                        f"\n[red]✗ Failed to send message: {result.error}[/]"
                    )
                    return 1
            finally:
                provider.disconnect()

        elif provider_config.provider_type == "napcat":
            from ...providers.qq_napcat import NapcatProvider, NapcatProviderConfig

            napcat_cfg = NapcatProviderConfig(
                provider_type="napcat",
                name=provider_config.name,
                http_url=provider_config.http_url or "",
                access_token=provider_config.access_token,
                timeout=provider_config.timeout or config.http.timeout,
                retry=provider_config.retry,
            )
            provider = NapcatProvider(napcat_cfg)
            provider.connect()
            try:
                result = provider.send_text(args.message, args.target)
                if result.success:
                    console.print("\n[green]✓ Message sent successfully![/]")
                    console.print(f"Message ID: {result.message_id}")
                else:
                    console.print(
                        f"\n[red]✗ Failed to send message: {result.error}[/]"
                    )
                    return 1
            finally:
                provider.disconnect()

        else:
            console.print(
                f"[red]Unsupported provider type: {provider_config.provider_type}[/]"
            )
            return 1

        return 0

    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_provider_status(args: argparse.Namespace) -> int:
    """Handle provider status command - show all providers status overview."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.providers:
            console.print("[yellow]No providers configured.[/]")
            return 0

        console.print("\n[bold]Provider Status Overview[/]\n")

        table = Table(title="Message Providers")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status")
        table.add_column("Target/URL")
        table.add_column("Features")

        for p in config.providers:
            status = "[green]Enabled[/]" if p.enabled else "[red]Disabled[/]"

            # Get target/URL info
            if p.provider_type == "feishu":
                url = p.webhook_url or "Not configured"
                if len(url) > 30:
                    url = url[:27] + "..."
                target = url
            elif p.provider_type == "napcat":
                target = p.http_url or "Not configured"
                if len(target) > 30:
                    target = target[:27] + "..."
            else:
                target = "-"

            # Features
            features = []
            if p.retry:
                features.append("retry")
            if p.circuit_breaker:
                features.append("circuit-breaker")
            if p.message_tracking:
                features.append("tracking")
            features_str = ", ".join(features) if features else "-"

            table.add_row(p.name, p.provider_type, status, target, features_str)

        console.print(table)

        # Summary
        enabled_count = sum(1 for p in config.providers if p.enabled)
        feishu_count = sum(
            1 for p in config.providers if p.provider_type == "feishu"
        )
        qq_count = sum(1 for p in config.providers if p.provider_type == "napcat")

        console.print("\n[bold]Summary:[/]")
        console.print(f"  Total: {len(config.providers)} providers")
        console.print(f"  Enabled: {enabled_count}")
        console.print(f"  Feishu: {feishu_count}, QQ/Napcat: {qq_count}")

        return 0

    except Exception as e:
        logger.error(f"Error getting provider status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_provider"]
