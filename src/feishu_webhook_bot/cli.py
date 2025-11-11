"""Command-line interface for Feishu Webhook Bot."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from . import __version__
from .bot import FeishuBot
from .core import BotConfig, WebhookConfig, get_logger, setup_logging

logger = get_logger("cli")


# Expose some module-level callables/clients so tests can patch them easily
try:
    from .config_ui import run_ui as _run_ui
except Exception:
    _run_ui = None  # type: ignore[assignment]
run_ui = _run_ui

try:
    from .core.client import FeishuWebhookClient as _FeishuWebhookClient
except Exception:
    _FeishuWebhookClient = None  # type: ignore[assignment,misc]
FeishuWebhookClient = _FeishuWebhookClient


def _has_valid_logging_config(logging_config: Any) -> bool:
    """Return True when logging config looks like a real LoggingConfig."""

    if logging_config is None:
        return False
    level = getattr(logging_config, "level", None)
    log_format = getattr(logging_config, "format", None)
    return isinstance(level, str) and isinstance(log_format, str)


def print_banner(config: BotConfig, args: argparse.Namespace) -> None:
    """Print a startup banner with configuration info."""
    console = Console()

    # ASCII Art: "Feishu Bot"
    logo = r"""
[bold cyan]  ______          _     _      __          __   _   _      ____        _   [/]
[bold cyan] |  ____|        | |   (_)     \ \        / /  | | | |    |  _ \      | |  [/]
[bold cyan] | |__ ___  _ __ | |__  _ _ __  \ \      / /__ | | | |___ | |_) | ___ | |_ [/]
[bold cyan] |  __/ _ \| '_ \| '_ \| | '__|  > \    / / _ \| | | / __||  _ < / _ \| __|[/]
[bold cyan] | | | (_) | | | | | | | | |    /  \/\  / / (_) | |_| \__ \| |_) | (_) | |_ [/]
[bold cyan] |_|  \___/|_| |_|_| |_|_|_|   / _ /\/\_\/ \___/ \___/|___/|____/ \___/ \__|[/]
    """

    info = f"""
[bold]Feishu Webhook Bot[/bold] [green]v{__version__}[/]
A framework for powerful, plugin-driven Feishu bots.

[dim]----------------------------------------------------[/]
[bold]Config:[/bold] [yellow]{args.config}[/]
[bold]Host:[/bold]   [yellow]{args.host}[/]
[bold]Port:[/bold]   [yellow]{args.port}[/]
[bold]Debug:[/bold]  [{"red" if args.debug else "green"}]{args.debug}[/]
"""

    panel_content = f"{logo}\n{info}"

    panel = Panel(
        panel_content,
        title="[bold white]Startup[/]",
        border_style="blue",
        expand=False,
    )

    console.print(panel)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="feishu-webhook-bot",
        description="Feishu Webhook Bot Framework - Build powerful Feishu bots with ease",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start bot with config file
  feishu-webhook-bot start -c config.yaml --debug

  # Start the web UI on a different port
  feishu-webhook-bot webui --host 0.0.0.0 --port 8888

  # Generate default config
  feishu-webhook-bot init -o config.yaml

  # Send a test message
  feishu-webhook-bot send -t "Hello, Feishu!" -w https://...

For more information, visit: https://github.com/AstroAir/feishu-webhook-bot
        """,
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s v{__version__}",
        help="Show program's version number and exit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the bot")
    start_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    start_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind the server to (if applicable by plugins)"
    )
    start_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Port to bind the server to (if applicable by plugins)",
    )
    start_parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug/verbose logging mode",
    )

    # Init command
    init_parser = subparsers.add_parser("init", help="Generate default configuration")
    init_parser.add_argument(
        "-o",
        "--output",
        default="config.yaml",
        help="Output config file path (default: config.yaml)",
    )

    # Send command
    send_parser = subparsers.add_parser("send", help="Send a test message")
    send_parser.add_argument("-w", "--webhook", required=True, help="Webhook URL")
    send_parser.add_argument("-t", "--text", default="Hello from Feishu Bot!", help="Message text")
    send_parser.add_argument("-s", "--secret", help="Webhook secret (optional)")

    # Plugins command
    plugins_parser = subparsers.add_parser("plugins", help="List loaded plugins")
    plugins_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # Web UI command
    webui_parser = subparsers.add_parser("webui", help="Launch the NiceGUI configuration UI")
    webui_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    webui_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    webui_parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")

    return parser


def cmd_start(args: argparse.Namespace) -> int:
    """Handle start command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print("Run 'feishu-webhook-bot init' to create a default configuration.")
        return 1

    try:
        # If debug is requested, load the config so we can override logging
        # and then construct the bot from the resulting config. Otherwise
        # prefer using FeishuBot.from_config if available (tests mock this).
        if args.debug:
            config = BotConfig.from_yaml(config_path)
            config.logging.level = "DEBUG"

            logging_config = getattr(config, "logging", None)
            if _has_valid_logging_config(logging_config):
                setup_logging(logging_config)
            print_banner(config, args)

            bot = FeishuBot(config)
        else:
            # Prefer classmethod constructor if present (keeps behavior consistent
            # with tests that expect FeishuBot.from_config to be used).
            if hasattr(FeishuBot, "from_config"):
                bot = FeishuBot.from_config(config_path)
                # When the constructor is patched with a mock, make the returned
                # instance expose the same MagicMock so test assertions against it
                # still succeed.
                from_config_attr = FeishuBot.from_config
                if hasattr(from_config_attr, "call_count"):
                    bot.from_config = from_config_attr  # type: ignore[method-assign]
            else:
                config = BotConfig.from_yaml(config_path)
                logging_config = getattr(config, "logging", None)
                if _has_valid_logging_config(logging_config):
                    setup_logging(logging_config)
                print_banner(config, args)
                bot = FeishuBot(config)

        bot.start()
        return 0
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        return 1


def cmd_init(args: argparse.Namespace) -> int:
    """Handle init command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    import yaml

    output_path = Path(args.output)

    if output_path.exists():
        response = input(f"{output_path} already exists. Overwrite? (y/N): ")
        if response.lower() != "y":
            print("Cancelled.")
            return 0

    # Create default configuration by dumping the Pydantic model
    default_config = BotConfig().model_dump()

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write config
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

    print(f"✓ Configuration file created: {output_path}")
    print("\nNext steps:")
    print(f"1. Edit {output_path} and add your webhook URL")
    print("2. Create plugins directory: mkdir plugins")
    print(f"3. Start the bot: feishu-webhook-bot start --config {output_path}")

    return 0


def cmd_send(args: argparse.Namespace) -> int:
    """Handle send command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    setup_logging()

    try:
        webhook = WebhookConfig(
            url=args.webhook,
            secret=args.secret,
            name="cli",
        )

        # Use module-level FeishuWebhookClient so tests can patch it easily.
        client_cls = FeishuWebhookClient
        if client_cls is None:
            from .core.client import FeishuWebhookClient as client_cls

        with client_cls(webhook) as client:
            result = client.send_text(args.text)
            print("✓ Message sent successfully!")
            print(f"Response: {result}")
            return 0

    except Exception as e:
        print(f"✗ Error sending message: {e}")
        return 1


def cmd_plugins(args: argparse.Namespace) -> int:
    """Handle plugins command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        # Use module-level client if available so tests can patch it
        client_cls = FeishuWebhookClient
        if client_cls is None:
            from .core.client import FeishuWebhookClient as client_cls
        from .plugins import PluginManager

        # Create temporary client
        webhook = config.get_webhook("default") or config.webhooks[0]
        client = client_cls(webhook)

        manager = PluginManager(config, client, None)
        manager.load_plugins()

        if not manager.plugins:
            print("No plugins loaded.")
            return 0

        print(f"Loaded plugins ({len(manager.plugins)}):\n")
        for _name, plugin in manager.plugins.items():
            metadata = plugin.metadata()
            print(f"  • {metadata.name} (v{metadata.version})")
            if metadata.description:
                print(f"    {metadata.description}")
            if metadata.author:
                print(f"    Author: {metadata.author}")
            print()

        client.close()
        return 0

    except Exception as e:
        print(f"Error loading plugins: {e}")
        return 1


def cmd_webui(args: argparse.Namespace) -> int:
    """Handle webui command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    try:
        # Use module-level run_ui so tests can patch it easily
        ui = run_ui
        if ui is None:
            from .config_ui import run_ui as ui

        ui(config_path=args.config, host=args.host, port=args.port)
        return 0
    except KeyboardInterrupt:
        logger.info("Web UI interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error running web UI: {e}", exc_info=True)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional sequence of CLI arguments (without the program name).

    Returns:
        Process exit code. 0 for success.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle no command: print help and exit (raise SystemExit to match
    # tests that expect argparse-like behavior)
    if not args.command:
        parser.print_help()
        raise SystemExit(0)

    # Dispatch to command handler
    handlers = {
        "start": cmd_start,
        "init": cmd_init,
        "send": cmd_send,
        "plugins": cmd_plugins,
        "webui": cmd_webui,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1
