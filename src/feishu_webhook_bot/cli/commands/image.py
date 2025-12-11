"""Image upload CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from ..base import BotConfig


def cmd_image(args: argparse.Namespace) -> int:
    """Handle image upload commands."""
    if not args.image_command:
        print("Usage: feishu-webhook-bot image <subcommand>")
        return 1

    handlers = {
        "upload": _cmd_image_upload,
        "permissions": _cmd_image_permissions,
        "configure": _cmd_image_configure,
    }

    handler = handlers.get(args.image_command)
    if handler:
        return handler(args)

    return 1


def _cmd_image_upload(args: argparse.Namespace) -> int:
    """Upload image to Feishu."""
    from ...core.image_uploader import FeishuImageUploader

    file_path = Path(args.file)
    if not file_path.exists():
        print("Error: Image file not found")
        return 1

    app_id = args.app_id
    app_secret = args.app_secret

    if not app_id or not app_secret:
        print("Error: Feishu app ID and secret are required")
        return 1

    try:
        console = Console()
        console.print("[yellow]Uploading image...[/]")

        uploader = FeishuImageUploader(app_id, app_secret)
        image_key = uploader.upload_image(file_path, image_type=args.type)

        console.print(f"[green]Image uploaded![/] Key: {image_key}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def _cmd_image_permissions(args: argparse.Namespace) -> int:
    """Check image upload permissions."""
    from ...core.image_uploader import (
        FeishuImageUploader,
        FeishuPermissionDeniedError,
    )

    app_id = args.app_id
    app_secret = args.app_secret

    if not app_id or not app_secret:
        print("Error: Feishu app ID and secret are required")
        return 1

    try:
        console = Console()
        console.print("[yellow]Checking permissions...[/]")

        uploader = FeishuImageUploader(app_id, app_secret, auto_open_auth=args.auto_fix)
        uploader.check_permissions()

        console.print("[green]Permissions check passed![/]")
        return 0

    except FeishuPermissionDeniedError as e:
        console = Console()
        console.print("[red]Permission denied[/]")
        if e.auth_url:
            console.print(f"Auth URL: {e.auth_url}")
        return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


def _cmd_image_configure(args: argparse.Namespace) -> int:
    """Configure image upload parameters."""
    config_path = Path(args.config)
    if not config_path.exists():
        print("Error: Configuration file not found")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        if args.app_id:
            config.app_id = args.app_id
        if args.app_secret:
            config.app_secret = args.app_secret

        config.to_yaml(config_path)

        console = Console()
        console.print("[green]Configuration updated![/]")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_image"]
