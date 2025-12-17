"""Automation CLI commands.

Provides comprehensive CLI interface for automation management including:
- List, status, and details viewing
- Create, edit, and delete rules
- Enable/disable rules
- Manual triggering with parameters
- Import/export rules
- Validation and testing
- Workflow templates management
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..base import BotConfig, logger

# Action type descriptions for CLI help
ACTION_TYPES = {
    "send_text": "Send text message",
    "send_template": "Send rendered template",
    "http_request": "Make HTTP request",
    "plugin_method": "Call plugin method",
    "python_code": "Execute Python code",
    "ai_chat": "AI chat completion",
    "ai_query": "AI query with context",
    "conditional": "Conditional branching",
    "loop": "Loop over items",
    "set_variable": "Set context variable",
    "delay": "Delay execution",
    "notify": "Send notification",
    "log": "Log message",
    "parallel": "Execute actions in parallel",
    "chain_rule": "Trigger another rule",
}

TRIGGER_TYPES = {
    "schedule": "Time-based trigger (cron or interval)",
    "event": "Event-based trigger",
    "webhook": "HTTP webhook trigger",
    "manual": "Manual trigger only",
    "chain": "Triggered by another rule",
}


def cmd_automation(args: argparse.Namespace) -> int:
    """Handle automation management commands.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    if not args.automation_command:
        print("Usage: feishu-webhook-bot automation <subcommand>")
        print("\nSubcommands:")
        print("  list      - List all automation rules")
        print("  status    - Show automation engine status")
        print("  details   - Show detailed rule information")
        print("  create    - Create a new automation rule")
        print("  edit      - Edit an existing rule")
        print("  delete    - Delete an automation rule")
        print("  enable    - Enable an automation rule")
        print("  disable   - Disable an automation rule")
        print("  trigger   - Manually trigger a rule")
        print("  run       - Run a rule with parameters")
        print("  test      - Test a rule configuration")
        print("  validate  - Validate rule configuration")
        print("  history   - View execution history")
        print("  import    - Import rules from file")
        print("  export    - Export rules to file")
        print("  templates - List workflow templates")
        return 1

    handlers = {
        "list": _cmd_automation_list,
        "status": _cmd_automation_status,
        "trigger": _cmd_automation_trigger,
        "run": _cmd_automation_run,
        "test": _cmd_automation_test,
        "validate": _cmd_automation_validate,
        "enable": _cmd_automation_enable,
        "disable": _cmd_automation_disable,
        "history": _cmd_automation_history,
        "details": _cmd_automation_details,
        "create": _cmd_automation_create,
        "edit": _cmd_automation_edit,
        "delete": _cmd_automation_delete,
        "import": _cmd_automation_import,
        "export": _cmd_automation_export,
        "templates": _cmd_automation_templates,
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
            info_lines.append(f"[bold]Default Webhooks:[/] {', '.join(rule.default_webhooks)}")

        for i, action in enumerate(rule.actions, 1):
            info_lines.append(f"  [green]Action {i}:[/] {action.type}")

        console.print("\n".join(info_lines))
        console.print("\n[yellow]Note: Full test execution requires bot runtime context.[/]")

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

        console.print(f"\n[bold]Automation Execution History: {args.rule_name}[/]\n")
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

        info_lines.append(f"[bold]Actions:[/] {len(rule.actions) if rule.actions else 0}")

        if rule.default_webhooks:
            info_lines.append(f"[bold]Default Webhooks:[/] {', '.join(rule.default_webhooks)}")

        # Actions details
        if rule.actions:
            info_lines.append("\n[bold]Actions:[/]")
            for i, action in enumerate(rule.actions, 1):
                action_type = action.type if hasattr(action, "type") else "unknown"
                info_lines.append(f"  {i}. {action_type}")

        console.print(Panel("\n".join(info_lines), title=f"Automation Details: {args.rule_name}"))
        return 0

    except Exception as e:
        logger.error(f"Error getting automation details: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_run(args: argparse.Namespace) -> int:
    """Handle automation run command with parameters."""
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

        # Parse parameters if provided
        params: dict[str, Any] = {}
        if hasattr(args, "params") and args.params:
            for param in args.params:
                if "=" in param:
                    key, value = param.split("=", 1)
                    # Try to parse as JSON for complex types
                    try:
                        params[key] = json.loads(value)
                    except json.JSONDecodeError:
                        params[key] = value

        console.print(f"\n[bold]Running Automation Rule: {args.rule_name}[/]\n")
        if params:
            console.print(f"[bold]Parameters:[/] {params}")

        # Show what would be executed
        console.print("\n[bold]Rule Configuration:[/]")
        console.print(f"  Trigger Type: {rule.trigger.type}")
        console.print(f"  Actions: {len(rule.actions)}")
        for i, action in enumerate(rule.actions, 1):
            console.print(f"    {i}. {action.type}")

        console.print("\n[yellow]Note: Full execution requires bot runtime context.[/]")
        console.print("Use the WebUI or API to trigger rules with full context.")

        return 0

    except Exception as e:
        logger.error(f"Error running automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_validate(args: argparse.Namespace) -> int:
    """Handle automation validate command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Validating Automation Rules...[/]\n")

        errors = []
        warnings = []

        for rule in config.automations:
            # Validate rule name
            if not rule.name:
                errors.append("Rule missing name")

            # Validate trigger
            if not rule.trigger:
                errors.append(f"Rule '{rule.name}': Missing trigger configuration")
            elif rule.trigger.type == "schedule" and not rule.trigger.schedule:
                errors.append(f"Rule '{rule.name}': Schedule trigger requires schedule config")
            elif rule.trigger.type == "event" and not rule.trigger.event:
                errors.append(f"Rule '{rule.name}': Event trigger requires event config")

            # Validate actions
            if not rule.actions:
                errors.append(f"Rule '{rule.name}': No actions defined")
            else:
                for i, action in enumerate(rule.actions, 1):
                    if action.type not in ACTION_TYPES:
                        warnings.append(
                            f"Rule '{rule.name}' action {i}: Unknown type '{action.type}'"
                        )

            # Check for disabled rules
            if not rule.enabled:
                warnings.append(f"Rule '{rule.name}': Rule is disabled")

        # Display results
        if errors:
            console.print("[red bold]Errors:[/]")
            for error in errors:
                console.print(f"  [red]✗[/] {error}")

        if warnings:
            console.print("\n[yellow bold]Warnings:[/]")
            for warning in warnings:
                console.print(f"  [yellow]⚠[/] {warning}")

        if not errors and not warnings:
            console.print("[green]✓ All automation rules are valid![/]")
            return 0
        elif not errors:
            console.print(f"\n[green]✓ Validation passed with {len(warnings)} warning(s)[/]")
            return 0
        else:
            console.print(f"\n[red]✗ Validation failed with {len(errors)} error(s)[/]")
            return 1

    except Exception as e:
        logger.error(f"Error validating automation rules: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_create(args: argparse.Namespace) -> int:
    """Handle automation create command."""
    config_path = Path(args.config)
    console = Console()

    try:
        if config_path.exists():
            config = BotConfig.from_yaml(config_path)
        else:
            console.print("[yellow]Config file not found, creating new one.[/]")
            config = BotConfig()

        # Interactive rule creation
        console.print("\n[bold]Create New Automation Rule[/]\n")

        name = Prompt.ask("Rule name")

        # Check if rule already exists
        for r in config.automations:
            if r.name == name:
                console.print(f"[red]Rule '{name}' already exists.[/]")
                return 1

        description = Prompt.ask("Description (optional)", default="")

        # Trigger type selection
        console.print("\n[bold]Available trigger types:[/]")
        for ttype, desc in TRIGGER_TYPES.items():
            console.print(f"  [cyan]{ttype}[/]: {desc}")
        trigger_type = Prompt.ask(
            "Trigger type", choices=list(TRIGGER_TYPES.keys()), default="schedule"
        )

        # Build trigger config
        trigger_config: dict[str, Any] = {"type": trigger_type}

        if trigger_type == "schedule":
            mode = Prompt.ask("Schedule mode", choices=["interval", "cron"], default="interval")
            if mode == "interval":
                minutes = Prompt.ask("Interval minutes", default="60")
                trigger_config["schedule"] = {
                    "mode": "interval",
                    "arguments": {"minutes": int(minutes)},
                }
            else:
                cron_expr = Prompt.ask("Cron expression (e.g., '0 9 * * *')")
                trigger_config["schedule"] = {"mode": "cron", "arguments": {"cron": cron_expr}}
        elif trigger_type == "event":
            event_type = Prompt.ask("Event type (e.g., 'im.message.receive_v1')")
            trigger_config["event"] = {"event_type": event_type}

        # Action type selection
        console.print("\n[bold]Available action types:[/]")
        for atype, desc in ACTION_TYPES.items():
            console.print(f"  [cyan]{atype}[/]: {desc}")

        actions: list[dict[str, Any]] = []
        while True:
            action_type = Prompt.ask("Action type (or 'done' to finish)", default="done")
            if action_type == "done":
                break

            if action_type not in ACTION_TYPES:
                console.print(f"[red]Unknown action type: {action_type}[/]")
                continue

            action_config: dict[str, Any] = {"type": action_type}

            if action_type == "send_text":
                action_config["text"] = Prompt.ask("Text to send")
            elif action_type == "send_template":
                action_config["template"] = Prompt.ask("Template name")
            elif action_type == "http_request":
                action_config["request"] = {
                    "method": Prompt.ask("HTTP method", default="GET"),
                    "url": Prompt.ask("URL"),
                }
            elif action_type == "delay":
                action_config["delay_seconds"] = float(Prompt.ask("Delay seconds", default="1"))
            elif action_type == "log":
                action_config["message"] = Prompt.ask("Log message")
                action_config["level"] = Prompt.ask("Log level", default="info")

            actions.append(action_config)
            console.print(f"[green]Added {action_type} action[/]")

        if not actions:
            console.print("[red]At least one action is required.[/]")
            return 1

        # Create rule dict
        rule_dict = {
            "name": name,
            "description": description or None,
            "enabled": True,
            "trigger": trigger_config,
            "actions": actions,
        }

        # Add to config
        from ...core.config import AutomationRule

        new_rule = AutomationRule.model_validate(rule_dict)
        config.automations.append(new_rule)
        config.save_yaml(config_path)

        console.print(f"\n[green]✓ Created automation rule: {name}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error creating automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_edit(args: argparse.Namespace) -> int:
    """Handle automation edit command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        rule = None
        rule_index = -1
        for i, r in enumerate(config.automations):
            if r.name == args.rule_name:
                rule = r
                rule_index = i
                break

        if not rule:
            console.print(f"[red]Automation rule not found: {args.rule_name}[/]")
            return 1

        console.print(f"\n[bold]Edit Automation Rule: {args.rule_name}[/]\n")

        # Show current config
        console.print("[bold]Current Configuration:[/]")
        console.print(f"  Description: {rule.description or 'N/A'}")
        console.print(f"  Enabled: {rule.enabled}")
        console.print(f"  Trigger: {rule.trigger.type}")
        console.print(f"  Actions: {len(rule.actions)}")

        # Edit fields
        new_desc = Prompt.ask(
            "New description (press Enter to keep)", default=rule.description or ""
        )
        if new_desc:
            rule.description = new_desc

        enable_str = Prompt.ask(
            "Enabled (y/n, press Enter to keep)", default="y" if rule.enabled else "n"
        )
        rule.enabled = enable_str.lower() == "y"

        # Save changes
        config.automations[rule_index] = rule
        config.save_yaml(config_path)

        console.print(f"\n[green]✓ Updated automation rule: {args.rule_name}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error editing automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_delete(args: argparse.Namespace) -> int:
    """Handle automation delete command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        rule_index = -1
        for i, r in enumerate(config.automations):
            if r.name == args.rule_name:
                rule_index = i
                break

        if rule_index < 0:
            console.print(f"[red]Automation rule not found: {args.rule_name}[/]")
            return 1

        # Confirm deletion
        if not Confirm.ask(f"Delete automation rule '{args.rule_name}'?"):
            console.print("[yellow]Deletion cancelled.[/]")
            return 0

        # Remove rule
        del config.automations[rule_index]
        config.save_yaml(config_path)

        console.print(f"[green]✓ Deleted automation rule: {args.rule_name}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error deleting automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_import(args: argparse.Namespace) -> int:
    """Handle automation import command."""
    config_path = Path(args.config)
    import_path = Path(args.import_file)
    console = Console()

    if not import_path.exists():
        console.print(f"[red]Import file not found: {import_path}[/]")
        return 1

    try:
        # Load existing config or create new
        config = BotConfig.from_yaml(config_path) if config_path.exists() else BotConfig()

        # Load import file
        with open(import_path) as f:
            import_data = json.load(f) if import_path.suffix == ".json" else yaml.safe_load(f)

        # Handle different import formats
        if isinstance(import_data, dict):
            if "automations" in import_data:
                rules_data = import_data["automations"]
            elif "rules" in import_data:
                rules_data = import_data["rules"]
            else:
                rules_data = [import_data]
        else:
            rules_data = import_data

        # Import rules
        from ...core.config import AutomationRule

        imported = 0
        skipped = 0
        existing_names = {r.name for r in config.automations}

        for rule_data in rules_data:
            name = rule_data.get("name")
            if name in existing_names:
                if hasattr(args, "overwrite") and args.overwrite:
                    # Remove existing rule
                    config.automations = [r for r in config.automations if r.name != name]
                else:
                    console.print(f"[yellow]Skipping '{name}' (already exists)[/]")
                    skipped += 1
                    continue

            try:
                rule = AutomationRule.model_validate(rule_data)
                config.automations.append(rule)
                imported += 1
                console.print(f"[green]Imported: {name}[/]")
            except Exception as e:
                console.print(f"[red]Failed to import '{name}': {e}[/]")
                skipped += 1

        config.save_yaml(config_path)

        console.print(f"\n[bold]Import complete:[/] {imported} imported, {skipped} skipped")
        return 0

    except Exception as e:
        logger.error(f"Error importing automation rules: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_export(args: argparse.Namespace) -> int:
    """Handle automation export command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    export_path = Path(args.export_file)
    console = Console()

    try:
        config = BotConfig.from_yaml(config_path)

        # Get rules to export
        if hasattr(args, "rule_names") and args.rule_names:
            rules = [r for r in config.automations if r.name in args.rule_names]
        else:
            rules = config.automations

        if not rules:
            console.print("[yellow]No rules to export.[/]")
            return 0

        # Convert to dict
        export_data = {"automations": [r.model_dump(exclude_none=True) for r in rules]}

        # Write to file
        with open(export_path, "w") as f:
            if export_path.suffix == ".json":
                json.dump(export_data, f, indent=2, default=str)
            else:
                yaml.safe_dump(export_data, f, default_flow_style=False)

        console.print(f"[green]✓ Exported {len(rules)} rule(s) to {export_path}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error exporting automation rules: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_templates(args: argparse.Namespace) -> int:
    """Handle automation templates command."""
    console = Console()

    try:
        from ...automation.workflow import BUILTIN_TEMPLATES

        console.print("\n[bold]Workflow Templates[/]\n")

        table = Table(title="Available Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Steps", style="green")
        table.add_column("Tags", style="magenta")

        for template in BUILTIN_TEMPLATES:
            table.add_row(
                template["name"],
                template.get("description", ""),
                str(len(template.get("steps", []))),
                ", ".join(template.get("tags", [])),
            )

        console.print(table)

        # Show action types reference
        if hasattr(args, "show_actions") and args.show_actions:
            console.print("\n[bold]Available Action Types:[/]\n")
            for atype, desc in ACTION_TYPES.items():
                console.print(f"  [cyan]{atype}[/]: {desc}")

        return 0

    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_automation"]
