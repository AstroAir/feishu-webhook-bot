"""Auth CLI commands."""

from __future__ import annotations

import argparse
import asyncio
import getpass

from rich.console import Console
from rich.table import Table


def cmd_auth(args: argparse.Namespace) -> int:
    """Handle authentication commands."""
    if not args.auth_command:
        print("Usage: feishu-webhook-bot auth <subcommand>")
        print("Subcommands: register, list-users, delete-user, unlock, verify")
        return 1

    handlers = {
        "register": _cmd_auth_register,
        "list-users": _cmd_auth_list_users,
        "delete-user": _cmd_auth_delete_user,
        "unlock": _cmd_auth_unlock,
        "verify": _cmd_auth_verify,
    }

    handler = handlers.get(args.auth_command)
    if handler:
        return handler(args)

    print(f"Unknown auth subcommand: {args.auth_command}")
    return 1


def _cmd_auth_register(args: argparse.Namespace) -> int:
    """Handle user registration command."""
    console = Console()

    console.print("\n[bold]Register New User[/]\n")
    console.print(f"Email: {args.email}")
    console.print(f"Username: {args.username}")

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm Password: ")
        if password != confirm:
            console.print("[red]Passwords do not match![/]")
            return 1

    try:
        from ...auth.service import AuthService

        auth_service = AuthService()
        user = asyncio.run(
            auth_service.register(
                email=args.email,
                username=args.username,
                password=password,
            )
        )

        console.print("\n[green]User registered successfully![/]")
        console.print(f"User ID: {user.id}")
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        console.print("The auth system requires the full bot installation.")
        return 1
    except Exception as e:
        console.print(f"[red]Registration failed:[/] {e}")
        return 1


def _cmd_auth_list_users(args: argparse.Namespace) -> int:
    """Handle list users command."""
    console = Console()

    console.print("\n[bold]Registered Users[/]\n")

    try:
        from ...auth.service import AuthService

        auth_service = AuthService()
        users = asyncio.run(auth_service.list_users())

        if not users:
            console.print("[yellow]No users registered.[/]")
            return 0

        table = Table(title="Users")
        table.add_column("ID", style="cyan")
        table.add_column("Username", style="magenta")
        table.add_column("Email")
        table.add_column("Verified")
        table.add_column("Locked")

        for user in users:
            verified = "[green]Yes[/]" if user.email_verified else "[red]No[/]"
            locked = "[red]Yes[/]" if user.is_locked else "[green]No[/]"
            table.add_row(str(user.id), user.username, user.email, verified, locked)

        console.print(table)
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        console.print("User listing requires auth database setup.")
        return 1
    except Exception as e:
        console.print(f"[red]Error listing users:[/] {e}")
        return 1


def _cmd_auth_delete_user(args: argparse.Namespace) -> int:
    """Handle delete user command."""
    console = Console()

    console.print(f"\n[bold]Deleting User: {args.user_id}[/]\n")

    try:
        from ...auth.service import AuthService

        auth_service = AuthService()
        asyncio.run(auth_service.delete_user(args.user_id))

        console.print(f"[green]User deleted: {args.user_id}[/]")
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        return 1
    except Exception as e:
        console.print(f"[red]Error deleting user:[/] {e}")
        return 1


def _cmd_auth_unlock(args: argparse.Namespace) -> int:
    """Handle unlock user command."""
    console = Console()

    console.print(f"\n[bold]Unlocking User: {args.user_id}[/]\n")

    try:
        from ...auth.service import AuthService

        auth_service = AuthService()
        asyncio.run(auth_service.unlock_user(args.user_id))

        console.print(f"[green]User unlocked: {args.user_id}[/]")
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        return 1
    except Exception as e:
        console.print(f"[red]Error unlocking user:[/] {e}")
        return 1


def _cmd_auth_verify(args: argparse.Namespace) -> int:
    """Handle verify user email command."""
    console = Console()

    console.print(f"\n[bold]Verifying User Email: {args.user_id}[/]\n")

    try:
        from ...auth.service import AuthService

        auth_service = AuthService()
        asyncio.run(auth_service.verify_email(args.user_id))

        console.print(f"[green]User email verified: {args.user_id}[/]")
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        return 1
    except Exception as e:
        console.print(f"[red]Error verifying email:[/] {e}")
        return 1


__all__ = ["cmd_auth"]
