"""Command-line interface for Feishu Webhook Bot."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .bot import FeishuBot
from .core import BotConfig, WebhookConfig, get_logger, setup_logging
from .core.client import CardBuilder

logger = get_logger("cli")


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
  feishu-webhook-bot start --config config.yaml

  # Generate default config
  feishu-webhook-bot init --output config.yaml

  # Send a test message
  feishu-webhook-bot send --text "Hello, Feishu!" --webhook https://...

  # List loaded plugins
  feishu-webhook-bot plugins --config config.yaml

For more information, visit: https://github.com/AstroAir/feishu-webhook-bot
        """,
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
    send_parser.add_argument(
        "-w", "--webhook", required=True, help="Webhook URL"
    )
    send_parser.add_argument(
        "-t", "--text", default="Hello from Feishu Bot!", help="Message text"
    )
    send_parser.add_argument(
        "-s", "--secret", help="Webhook secret (optional)"
    )

    # Plugins command
    plugins_parser = subparsers.add_parser("plugins", help="List loaded plugins")
    plugins_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # Version command
    subparsers.add_parser("version", help="Show version information")

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
        bot = FeishuBot.from_config(config_path)
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

    # Create default configuration
    default_config = {
        "webhooks": [
            {
                "name": "default",
                "url": "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL",
                "secret": None,
            }
        ],
        "scheduler": {
            "enabled": True,
            "timezone": "Asia/Shanghai",
            "job_store_type": "memory",
        },
        "plugins": {
            "enabled": True,
            "plugin_dir": "plugins",
            "auto_reload": True,
            "reload_delay": 1.0,
        },
        "logging": {
            "level": "INFO",
            "log_file": "logs/bot.log",
            "max_bytes": 10485760,
            "backup_count": 5,
        },
    }

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

        from .core.client import FeishuWebhookClient

        with FeishuWebhookClient(webhook) as client:
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
        from .plugins import PluginManager
        from .core.client import FeishuWebhookClient

        # Create temporary client
        webhook = config.get_webhook("default") or config.webhooks[0]
        client = FeishuWebhookClient(webhook)

        manager = PluginManager(config, client, None)
        manager.load_plugins()

        if not manager.plugins:
            print("No plugins loaded.")
            return 0

        print(f"Loaded plugins ({len(manager.plugins)}):\n")
        for name, plugin in manager.plugins.items():
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


def cmd_version(args: argparse.Namespace) -> int:
    """Handle version command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    from . import __version__

    print(f"Feishu Webhook Bot v{__version__}")
    return 0


def cmd_webui(args: argparse.Namespace) -> int:
    """Handle webui command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    try:
        from .config_ui import run_ui

        run_ui(config_path=args.config, host=args.host, port=args.port)
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

    # Handle no command
    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handler
    handlers = {
        "start": cmd_start,
        "init": cmd_init,
        "send": cmd_send,
        "plugins": cmd_plugins,
        "version": cmd_version,
        "webui": cmd_webui,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1
