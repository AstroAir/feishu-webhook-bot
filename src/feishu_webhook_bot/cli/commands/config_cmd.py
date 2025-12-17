"""Config CLI commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console

from ..base import BotConfig, logger


def cmd_config(args: argparse.Namespace) -> int:
    """Handle configuration commands."""
    if not args.config_command:
        print("Usage: feishu-webhook-bot config <subcommand>")
        print("Subcommands: validate, view, set, reload, export, import")
        return 1

    handlers = {
        "validate": _cmd_config_validate,
        "view": _cmd_config_view,
        "set": _cmd_config_set,
        "reload": _cmd_config_reload,
        "export": _cmd_config_export,
        "import": _cmd_config_import,
    }

    handler = handlers.get(args.config_command)
    if handler:
        return handler(args)

    print(f"Unknown config subcommand: {args.config_command}")
    return 1


def _cmd_config_validate(args: argparse.Namespace) -> int:
    """Handle config validate command."""
    config_path = Path(args.config)
    console = Console()

    console.print(f"\n[bold]Validating Configuration: {config_path}[/]\n")

    if not config_path.exists():
        console.print(f"[red]Error: Configuration file not found: {config_path}[/]")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console.print("[green]Configuration is valid![/]\n")

        # Show summary (use getattr for safe access)
        summary = [
            f"[bold]Webhooks:[/] {len(config.webhooks) if config.webhooks else 0}",
            f"[bold]Providers:[/] {len(config.providers) if config.providers else 0}",
            f"[bold]Tasks:[/] {len(config.tasks) if config.tasks else 0}",
            f"[bold]Automations:[/] {len(config.automations) if config.automations else 0}",
            f"[bold]Plugins Path:[/] {getattr(config, 'plugins_dir', 'plugins')}",
            f"[bold]AI Enabled:[/] {config.ai.enabled if config.ai else False}",
        ]

        console.print("\n".join(summary))
        return 0

    except Exception as e:
        console.print("[red]Configuration validation failed:[/]")
        console.print(f"  {e}")
        return 1


def _cmd_config_view(args: argparse.Namespace) -> int:
    """Handle config view command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if args.section:
            # View specific section
            section_data = getattr(config, args.section, None)
            if section_data is None:
                console.print(f"[red]Section not found: {args.section}[/]")
                console.print(
                    "Available sections: webhooks, providers, tasks, "
                    "automations, scheduler, ai, logging, http"
                )
                return 1

            console.print(f"\n[bold]Configuration Section: {args.section}[/]\n")

            if hasattr(section_data, "model_dump"):
                data = section_data.model_dump()
            elif isinstance(section_data, list):
                data = [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in section_data
                ]
            else:
                data = section_data

            console.print(json.dumps(data, indent=2, default=str))
        else:
            # View full config summary
            console.print(f"\n[bold]Configuration: {config_path}[/]\n")

            sections = [
                "webhooks",
                "providers",
                "tasks",
                "automations",
                "scheduler",
                "ai",
                "logging",
            ]
            for section in sections:
                data = getattr(config, section, None)
                if data:
                    if isinstance(data, list):
                        console.print(f"[cyan]{section}:[/] {len(data)} items")
                    else:
                        console.print(f"[cyan]{section}:[/] configured")
                else:
                    console.print(f"[dim]{section}:[/] not configured")

        return 0

    except Exception as e:
        logger.error(f"Error viewing config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_config_set(args: argparse.Namespace) -> int:
    """Handle config set command."""
    import yaml

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        # Load raw YAML to modify
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Parse dot notation key
        keys = args.key.split(".")
        current = data

        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set value (try to parse as JSON for complex values)
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value

        current[keys[-1]] = value

        # Save
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        console = Console()
        console.print(f"[green]Set {args.key} = {args.value}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error setting config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_config_reload(args: argparse.Namespace) -> int:
    """Handle config reload command."""
    console = Console()

    console.print("\n[bold]Configuration Reload[/]\n")
    console.print("[yellow]Note: Configuration reload requires a running bot.[/]")
    console.print(
        "The bot watches for config file changes automatically if config_watcher is enabled."
    )
    console.print("\nAlternatively, restart the bot to load new configuration.")

    return 0


def _cmd_config_export(args: argparse.Namespace) -> int:
    """Handle config export command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        output_path = Path(args.output)

        if args.format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(config.model_dump(), f, indent=2, default=str)
        else:
            import yaml

            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(config.model_dump(), f, default_flow_style=False, allow_unicode=True)

        console = Console()
        console.print(f"[green]Configuration exported to: {output_path}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error exporting config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_config_import(args: argparse.Namespace) -> int:
    """Handle config import command."""
    import yaml

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    config_path = Path(args.config)

    try:
        # Load input file
        with open(input_path, encoding="utf-8") as f:
            input_data = json.load(f) if input_path.suffix == ".json" else yaml.safe_load(f)

        if args.merge and config_path.exists():
            # Merge with existing config
            with open(config_path, encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}

            # Deep merge
            def deep_merge(base, update):
                for key, value in update.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base

            merged = deep_merge(existing, input_data)
            input_data = merged

        # Validate by loading as config
        _ = BotConfig(**input_data)

        # Save
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(input_data, f, default_flow_style=False, allow_unicode=True)

        console = Console()
        console.print(f"[green]Configuration imported to: {config_path}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error importing config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_config"]
