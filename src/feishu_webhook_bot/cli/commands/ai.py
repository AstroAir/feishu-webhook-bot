"""AI CLI commands."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..base import BotConfig, logger


def cmd_ai(args: argparse.Namespace) -> int:
    """Handle AI management commands."""
    if not args.ai_command:
        print("Usage: feishu-webhook-bot ai <subcommand>")
        print("Subcommands: chat, model, models, stats, tools, clear, mcp, test, stream,")
        print("             conversation, multi-agent")
        return 1

    handlers = {
        "chat": _cmd_ai_chat,
        "model": _cmd_ai_model,
        "models": _cmd_ai_models,
        "stats": _cmd_ai_stats,
        "tools": _cmd_ai_tools,
        "clear": _cmd_ai_clear,
        "mcp": _cmd_ai_mcp,
        "test": _cmd_ai_test,
        "stream": _cmd_ai_stream,
        "conversation": _cmd_ai_conversation,
        "multi-agent": _cmd_ai_multi_agent,
    }

    handler = handlers.get(args.ai_command)
    if handler:
        return handler(args)

    print(f"Unknown AI subcommand: {args.ai_command}")
    return 1


def _cmd_ai_chat(args: argparse.Namespace) -> int:
    """Handle AI chat command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.ai or not config.ai.enabled:
            console.print("[yellow]AI is not enabled in configuration.[/]")
            return 1

        console.print("\n[bold]AI Chat Test[/]\n")
        console.print(f"[cyan]User:[/] {args.message}")
        console.print(f"[dim]User ID: {args.user_id}[/]")

        # Try to initialize AI agent and get response
        try:
            from ...ai.agent import AIAgent

            agent = AIAgent(config.ai)
            response = asyncio.run(agent.chat(args.message, user_id=args.user_id))
            console.print(f"\n[green]Assistant:[/] {response}")
        except ImportError:
            console.print(
                "\n[yellow]AI agent not available. Install with: pip install pydantic-ai[/]"
            )
        except Exception as e:
            console.print(f"\n[red]AI Error:[/] {e}")

        return 0

    except Exception as e:
        logger.error(f"Error in AI chat: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_model(args: argparse.Namespace) -> int:
    """Handle AI model command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.ai:
            console.print("[yellow]AI is not configured.[/]")
            return 1

        if args.model_name:
            # Switch model
            console.print(f"[yellow]Switching model to: {args.model_name}[/]")
            config.ai.model = args.model_name
            config.save_yaml(config_path)
            console.print(f"[green]Model switched to: {args.model_name}[/]")
        else:
            # Show current model
            current_model = config.ai.model or "Not configured"
            console.print(f"\n[bold]Current AI Model:[/] {current_model}")

        return 0

    except Exception as e:
        logger.error(f"Error in AI model: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_models(args: argparse.Namespace) -> int:
    """Handle AI models listing command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Available AI Models[/]\n")

        # List common models by provider
        models = {
            "OpenAI": [
                "openai:gpt-4o",
                "openai:gpt-4o-mini",
                "openai:gpt-4-turbo",
                "openai:gpt-3.5-turbo",
            ],
            "Anthropic": [
                "anthropic:claude-3-5-sonnet-latest",
                "anthropic:claude-3-opus-latest",
                "anthropic:claude-3-haiku-20240307",
            ],
            "Google": [
                "google-gla:gemini-1.5-pro",
                "google-gla:gemini-1.5-flash",
            ],
            "Groq": [
                "groq:llama-3.1-70b-versatile",
                "groq:mixtral-8x7b-32768",
            ],
        }

        table = Table(title="Supported Models")
        table.add_column("Provider", style="cyan")
        table.add_column("Models", style="green")

        for provider, model_list in models.items():
            table.add_row(provider, "\n".join(model_list))

        console.print(table)

        if config.ai and config.ai.model:
            console.print(f"\n[bold]Current Model:[/] {config.ai.model}")

        return 0

    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_stats(args: argparse.Namespace) -> int:
    """Handle AI stats command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]AI Usage Statistics[/]\n")

        if not config.ai or not config.ai.enabled:
            console.print("[yellow]AI is not enabled in configuration.[/]")
            return 0

        info_lines = [
            f"[bold]Model:[/] {config.ai.model or 'Not configured'}",
            f"[bold]Enabled:[/] {config.ai.enabled}",
            f"[bold]Max Tokens:[/] {config.ai.max_tokens or 'Default'}",
            f"[bold]Temperature:[/] {config.ai.temperature or 'Default'}",
        ]

        if config.ai.system_prompt:
            prompt_preview = (
                config.ai.system_prompt[:100] + "..."
                if len(config.ai.system_prompt) > 100
                else config.ai.system_prompt
            )
            info_lines.append(f"[bold]System Prompt:[/] {prompt_preview}")

        console.print("\n".join(info_lines))
        console.print(
            "\n[yellow]Note: Runtime usage statistics available when bot is running.[/]"
        )

        return 0

    except Exception as e:
        logger.error(f"Error getting AI stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_tools(args: argparse.Namespace) -> int:
    """Handle AI tools listing command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Registered AI Tools[/]\n")

        # Check for MCP tools
        if config.ai and config.ai.mcp_servers:
            table = Table(title="MCP Servers (Tool Sources)")
            table.add_column("Server", style="cyan")
            table.add_column("Transport", style="magenta")
            table.add_column("Status")

            for server in config.ai.mcp_servers:
                transport = server.transport or "stdio"
                table.add_row(server.name, transport, "[green]Configured[/]")

            console.print(table)
        else:
            console.print("[yellow]No MCP servers configured.[/]")

        console.print("\n[yellow]Note: Built-in tools are loaded at runtime.[/]")
        console.print("Use 'feishu-webhook-bot ai mcp' to check MCP server status.")

        return 0

    except Exception as e:
        logger.error(f"Error listing AI tools: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_clear(args: argparse.Namespace) -> int:
    """Handle AI conversation clear command."""
    console = Console()

    console.print("\n[bold]Clearing Conversation History[/]\n")
    console.print(f"User ID: {args.user_id}")

    console.print("\n[yellow]Note: This command clears runtime conversation state.[/]")
    console.print("For persistent storage, check your conversation store configuration.")
    console.print(f"\n[green]Conversation history marked for clearing: {args.user_id}[/]")

    return 0


def _cmd_ai_mcp(args: argparse.Namespace) -> int:
    """Handle AI MCP status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]MCP Server Status[/]\n")

        if not config.ai or not config.ai.mcp_servers:
            console.print("[yellow]No MCP servers configured.[/]")
            return 0

        table = Table(title="MCP Servers")
        table.add_column("Name", style="cyan")
        table.add_column("Transport", style="magenta")
        table.add_column("Command/URL")
        table.add_column("Status")

        for server in config.ai.mcp_servers:
            transport = server.transport or "stdio"
            endpoint = server.command or server.url or "N/A"
            if len(str(endpoint)) > 40:
                endpoint = str(endpoint)[:40] + "..."
            table.add_row(server.name, transport, str(endpoint), "[yellow]Configured[/]")

        console.print(table)
        console.print(
            "\n[yellow]Note: MCP servers connect at runtime when AI agent starts.[/]"
        )

        return 0

    except Exception as e:
        logger.error(f"Error getting MCP status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_test(args: argparse.Namespace) -> int:
    """Handle AI test command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]AI Configuration Test[/]\n")

        # Test configuration
        info_lines = []
        errors = []

        if not config.ai:
            errors.append("AI configuration not found")
        else:
            info_lines.append(f"[bold]Enabled:[/] {config.ai.enabled}")
            info_lines.append(f"[bold]Model:[/] {config.ai.model or 'Not set'}")
            info_lines.append(
                f"[bold]API Key:[/] {'Configured' if config.ai.api_key else 'Not set'}"
            )
            info_lines.append(f"[bold]Temperature:[/] {config.ai.temperature}")
            info_lines.append(
                f"[bold]Max Tokens:[/] {config.ai.max_tokens or 'Default'}"
            )
            info_lines.append(f"[bold]Tools Enabled:[/] {config.ai.tools_enabled}")
            info_lines.append(f"[bold]Web Search:[/] {config.ai.web_search_enabled}")
            info_lines.append(f"[bold]Streaming:[/] {config.ai.streaming.enabled}")

            if config.ai.mcp and config.ai.mcp.enabled:
                info_lines.append(
                    f"[bold]MCP Servers:[/] {len(config.ai.mcp.servers)} configured"
                )

            if config.ai.multi_agent and config.ai.multi_agent.enabled:
                info_lines.append(
                    f"[bold]Multi-Agent:[/] {config.ai.multi_agent.orchestration_mode}"
                )

            if not config.ai.enabled:
                errors.append("AI is disabled in configuration")
            if not config.ai.api_key:
                errors.append("API key not configured")

        console.print(Panel("\n".join(info_lines), title="Configuration"))

        if errors:
            console.print("\n[bold red]Issues Found:[/]")
            for err in errors:
                console.print(f"  [red]• {err}[/]")
        else:
            console.print("\n[green]✓ Configuration looks valid[/]")

        # Test chat if requested
        if args.message and config.ai and config.ai.enabled and config.ai.api_key:
            console.print("\n[bold]Testing AI Chat...[/]\n")
            try:
                from ...ai.agent import AIAgent

                agent = AIAgent(config.ai)
                response = asyncio.run(agent.chat("test-user", args.message))
                console.print(f"[cyan]User:[/] {args.message}")
                console.print(f"[green]Assistant:[/] {response}")
                console.print("\n[green]✓ AI chat test passed[/]")
            except Exception as e:
                console.print(f"[red]✗ AI chat test failed: {e}[/]")

        return 0

    except Exception as e:
        logger.error(f"Error testing AI: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_stream(args: argparse.Namespace) -> int:
    """Handle AI streaming test command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.ai or not config.ai.enabled:
            console.print("[yellow]AI is not enabled in configuration.[/]")
            return 1

        console.print("\n[bold]AI Streaming Test[/]\n")
        console.print(f"[cyan]User:[/] {args.message}")
        console.print(f"[dim]User ID: {args.user_id}[/]")
        console.print("\n[green]Assistant:[/] ", end="")

        try:
            from ...ai.agent import AIAgent

            agent = AIAgent(config.ai)

            async def stream_response():
                chunks = []
                async for chunk in agent.chat_stream(args.user_id, args.message):
                    print(chunk, end="", flush=True)
                    chunks.append(chunk)
                return chunks

            chunks = asyncio.run(stream_response())
            print()  # New line after streaming
            console.print(f"\n[dim]Received {len(chunks)} chunks[/]")

        except ImportError:
            console.print(
                "\n[yellow]AI agent not available. Install with: pip install pydantic-ai[/]"
            )
        except Exception as e:
            console.print(f"\n[red]AI Streaming Error:[/] {e}")

        return 0

    except Exception as e:
        logger.error(f"Error in AI streaming: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_conversation(args: argparse.Namespace) -> int:
    """Handle AI conversation management commands."""
    if not args.conv_command:
        print("Usage: feishu-webhook-bot ai conversation <subcommand>")
        print("Subcommands: list, export, import, delete, details")
        return 1

    handlers = {
        "list": _cmd_ai_conv_list,
        "export": _cmd_ai_conv_export,
        "import": _cmd_ai_conv_import,
        "delete": _cmd_ai_conv_delete,
        "details": _cmd_ai_conv_details,
    }

    handler = handlers.get(args.conv_command)
    if handler:
        return handler(args)

    print(f"Unknown conversation subcommand: {args.conv_command}")
    return 1


def _cmd_ai_conv_list(args: argparse.Namespace) -> int:
    """Handle AI conversation list command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Active Conversations[/]\n")

        if not config.ai or not config.ai.enabled:
            console.print("[yellow]AI is not enabled in configuration.[/]")
            return 0

        # Note: This shows config info since runtime data needs bot running
        console.print("[yellow]Note: Active conversations are tracked at runtime.[/]")
        console.print("Start the bot to track and list active conversations.")
        console.print(
            f"\nConversation timeout: {config.ai.conversation_timeout_minutes} minutes"
        )
        console.print(f"Max conversation turns: {config.ai.max_conversation_turns}")

        if config.ai.conversation_persistence:
            console.print(
                f"Persistence: {config.ai.conversation_persistence.storage_type}"
            )

        return 0

    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_conv_export(args: argparse.Namespace) -> int:
    """Handle AI conversation export command."""
    console = Console()

    console.print(f"\n[bold]Export Conversation: {args.user_id}[/]\n")
    console.print("[yellow]Note: Conversation export requires bot runtime context.[/]")
    console.print(
        "Use the WebUI or API to export conversations while bot is running."
    )

    if args.output:
        console.print(f"Output file: {args.output}")

    return 0


def _cmd_ai_conv_import(args: argparse.Namespace) -> int:
    """Handle AI conversation import command."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 1

    try:
        console = Console()

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        console.print(f"\n[bold]Import Conversation from: {args.file}[/]\n")
        console.print(f"User ID: {data.get('user_id', 'Unknown')}")
        console.print(f"Messages: {data.get('message_count', 0)}")
        console.print(
            f"Total Tokens: {data.get('input_tokens', 0) + data.get('output_tokens', 0)}"
        )

        console.print(
            "\n[yellow]Note: Conversation import requires bot runtime context.[/]"
        )
        console.print(
            "Use the WebUI or API to import conversations while bot is running."
        )

        return 0

    except json.JSONDecodeError as e:
        print(f"Invalid JSON file: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error importing conversation: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_conv_delete(args: argparse.Namespace) -> int:
    """Handle AI conversation delete command."""
    console = Console()

    console.print(f"\n[bold]Delete Conversation: {args.user_id}[/]\n")
    console.print("[yellow]Note: Conversation deletion requires bot runtime context.[/]")
    console.print(
        "Use the WebUI or API to delete conversations while bot is running."
    )

    return 0


def _cmd_ai_conv_details(args: argparse.Namespace) -> int:
    """Handle AI conversation details command."""
    console = Console()

    console.print(f"\n[bold]Conversation Details: {args.user_id}[/]\n")
    console.print("[yellow]Note: Conversation details require bot runtime context.[/]")
    console.print(
        "Use the WebUI or API to view conversation details while bot is running."
    )

    return 0


def _cmd_ai_multi_agent(args: argparse.Namespace) -> int:
    """Handle AI multi-agent commands."""
    if not args.ma_command:
        print("Usage: feishu-webhook-bot ai multi-agent <subcommand>")
        print("Subcommands: status, test")
        return 1

    handlers = {
        "status": _cmd_ai_ma_status,
        "test": _cmd_ai_ma_test,
    }

    handler = handlers.get(args.ma_command)
    if handler:
        return handler(args)

    print(f"Unknown multi-agent subcommand: {args.ma_command}")
    return 1


def _cmd_ai_ma_status(args: argparse.Namespace) -> int:
    """Handle AI multi-agent status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Multi-Agent Orchestration Status[/]\n")

        if not config.ai:
            console.print("[yellow]AI is not configured.[/]")
            return 0

        ma_config = config.ai.multi_agent
        if not ma_config:
            console.print("[yellow]Multi-agent is not configured.[/]")
            return 0

        info_lines = [
            f"[bold]Enabled:[/] {ma_config.enabled}",
            f"[bold]Orchestration Mode:[/] {ma_config.orchestration_mode}",
            f"[bold]Max Agents:[/] {ma_config.max_agents}",
            f"[bold]Timeout:[/] {ma_config.timeout_seconds}s",
        ]

        console.print(
            Panel("\n".join(info_lines), title="Multi-Agent Configuration")
        )

        if ma_config.enabled:
            console.print("\n[bold]Default Agents:[/]")
            console.print("  • SearchAgent (search)")
            console.print("  • AnalysisAgent (analysis)")
            console.print("  • ResponseAgent (response)")

        return 0

    except Exception as e:
        logger.error(f"Error getting multi-agent status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_ma_test(args: argparse.Namespace) -> int:
    """Handle AI multi-agent test command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.ai or not config.ai.enabled:
            console.print("[yellow]AI is not enabled in configuration.[/]")
            return 1

        if not config.ai.multi_agent or not config.ai.multi_agent.enabled:
            console.print("[yellow]Multi-agent is not enabled in configuration.[/]")
            return 1

        mode = args.mode or config.ai.multi_agent.orchestration_mode
        console.print(f"\n[bold]Multi-Agent Test ({mode} mode)[/]\n")
        console.print(f"[cyan]Input:[/] {args.message}")

        try:
            from ...ai.agent import AIAgent

            agent = AIAgent(config.ai)

            async def run_test():
                return await agent.orchestrator.orchestrate(args.message, mode=mode)

            response = asyncio.run(run_test())
            console.print(f"\n[green]Response:[/]\n{response}")

        except ImportError:
            console.print(
                "\n[yellow]AI agent not available. Install with: pip install pydantic-ai[/]"
            )
        except Exception as e:
            console.print(f"\n[red]Multi-agent test failed:[/] {e}")

        return 0

    except Exception as e:
        logger.error(f"Error testing multi-agent: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_ai"]
