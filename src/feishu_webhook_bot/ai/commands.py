"""Chat command system for handling user commands like /help, /reset, /model, etc.

This module provides:
- CommandResult: Data class for command execution results
- CommandHandler: Main command handler with built-in and custom commands
- Support for command registration and execution
- Comprehensive help system
- Conversation and model management
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger
from ..core.message_handler import IncomingMessage

if TYPE_CHECKING:
    from .agent import AIAgent
    from .conversation import ConversationManager
    from .conversation_store import PersistentConversationManager

logger = get_logger("ai.commands")

# Type alias for command handler functions (without self, as it's a bound method)
CommandFunc = Callable[[IncomingMessage, list[str]], Awaitable["CommandResult"]]


@dataclass
class CommandResult:
    """Result of command execution.

    Attributes:
        success: Whether the command executed successfully
        response: Response text to send back to the user
        should_continue: Whether to continue with AI processing after command
        data: Additional data returned by the command handler
    """

    success: bool
    response: str
    should_continue: bool = False
    data: dict[str, Any] | None = None


class CommandHandler:
    """Handle chat commands and intent recognition.

    Provides built-in commands for common operations and supports custom command
    registration. Commands are case-insensitive and support arguments.

    Built-in commands:
    - /help: Show help information
    - /reset: Reset current conversation
    - /history: Show conversation history summary
    - /model: Switch AI model (if available_models configured)
    - /stats: Show usage statistics
    - /clear: Clear conversation context

    Example:
        ```python
        handler = CommandHandler(ai_agent, conversation_manager)

        # Register custom command
        @handler.register("/weather")
        async def weather_cmd(handler, message, args):
            return CommandResult(True, f"Weather for {args[0]}...")

        # Process message
        is_cmd, result = await handler.process(message)
        if is_cmd:
            await send_reply(message, result.response)
        ```
    """

    BUILTIN_COMMANDS: dict[str, str] = {
        "/help": "显示帮助信息",
        "/reset": "重置当前对话，清除上下文",
        "/history": "显示对话历史摘要",
        "/model": "切换AI模型 (用法: /model gpt-4o)",
        "/persona": "管理AI人格预设 (用法: /persona list|show|set|reset)",
        "/stats": "显示使用统计",
        "/clear": "清除当前会话的上下文",
    }

    # QQ-specific commands (only shown for QQ platform)
    QQ_COMMANDS: dict[str, str] = {
        "/poke": "戳一戳 (用法: /poke [@用户])",
        "/mute": "禁言群成员 (用法: /mute @用户 [分钟数])",
        "/unmute": "解除禁言 (用法: /unmute @用户)",
        "/kick": "踢出群成员 (用法: /kick @用户)",
        "/status": "查看Bot在线状态",
        "/groupinfo": "查看群信息",
    }

    def __init__(
        self,
        ai_agent: AIAgent | None = None,
        conversation_manager: ConversationManager | None = None,
        command_prefix: str = "/",
        available_models: list[str] | None = None,
        qq_provider: Any | None = None,
        conversation_store: PersistentConversationManager | None = None,
    ) -> None:
        """Initialize command handler.

        Args:
            ai_agent: AI agent instance for model-related operations
            conversation_manager: Conversation manager instance for conversation operations
            command_prefix: Prefix for commands (default: "/")
            available_models: List of models available for switching
            qq_provider: QQ/Napcat provider for QQ-specific commands
        """
        self.ai_agent = ai_agent
        self.conv_manager = conversation_manager
        self.prefix = command_prefix
        self.available_models = available_models or []
        self.qq_provider = qq_provider
        self.conversation_store = conversation_store
        self._custom_commands: dict[str, CommandFunc] = {}

        # Register built-in handlers
        self._handlers: dict[str, CommandFunc] = {
            "/help": self._handle_help,
            "/reset": self._handle_reset,
            "/history": self._handle_history,
            "/model": self._handle_model,
            "/persona": self._handle_persona,
            "/stats": self._handle_stats,
            "/clear": self._handle_clear,
            # QQ-specific commands
            "/poke": self._handle_poke,
            "/mute": self._handle_mute,
            "/unmute": self._handle_unmute,
            "/kick": self._handle_kick,
            "/status": self._handle_status,
            "/groupinfo": self._handle_groupinfo,
        }

        logger.debug(
            "CommandHandler initialized with prefix='%s', models=%s, qq_provider=%s",
            self.prefix,
            self.available_models,
            qq_provider is not None,
        )

    def register(self, name: str) -> Callable[[CommandFunc], CommandFunc]:
        """Decorator to register a custom command.

        The command name is automatically converted to lowercase.

        Args:
            name: Command name (e.g., "/weather")

        Returns:
            Decorator function

        Example:
            ```python
            @handler.register("/weather")
            async def weather_cmd(handler, message, args):
                return CommandResult(True, f"Weather for {args[0]}...")
            ```

        Raises:
            ValueError: If command name doesn't start with the prefix
            ValueError: If command is already registered
        """

        def decorator(func: CommandFunc) -> CommandFunc:
            cmd_lower = name.lower()

            # Validate command name
            if not cmd_lower.startswith(self.prefix):
                raise ValueError(f"Command '{name}' must start with prefix '{self.prefix}'")

            if cmd_lower in self._handlers or cmd_lower in self._custom_commands:
                raise ValueError(f"Command '{cmd_lower}' is already registered")

            self._custom_commands[cmd_lower] = func
            logger.info("Registered custom command: %s", cmd_lower)

            return func

        return decorator

    def unregister(self, name: str) -> bool:
        """Unregister a custom command.

        Args:
            name: Command name (e.g., "/weather")

        Returns:
            True if command was unregistered, False if not found
        """
        cmd_lower = name.lower()

        if cmd_lower in self._custom_commands:
            del self._custom_commands[cmd_lower]
            logger.info("Unregistered custom command: %s", cmd_lower)
            return True

        if cmd_lower in self._handlers:
            logger.warning("Cannot unregister built-in command: %s", cmd_lower)
            return False

        logger.debug("Command not found for unregister: %s", cmd_lower)
        return False

    def is_command(self, text: str) -> bool:
        """Check if text is a command.

        Args:
            text: Text to check

        Returns:
            True if text starts with command prefix
        """
        return text.strip().startswith(self.prefix)

    def parse_command(self, text: str) -> tuple[str, list[str]]:
        """Parse command text into command name and arguments.

        Args:
            text: Full command text (e.g., "/model gpt-4o")

        Returns:
            Tuple of (command_name_lowercase, arguments_list)

        Example:
            ```python
            cmd, args = handler.parse_command("/model gpt-4o foo bar")
            assert cmd == "/model"
            assert args == ["gpt-4o", "foo", "bar"]
            ```
        """
        parts = text.strip().split()
        cmd = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args

    async def process(
        self,
        message: IncomingMessage,
    ) -> tuple[bool, CommandResult | None]:
        """Process a message for commands.

        Checks if the message is a command and executes it if found.

        Args:
            message: Incoming message

        Returns:
            Tuple of (is_command, result)
            If is_command is False, result is None

        Example:
            ```python
            is_cmd, result = await handler.process(message)
            if is_cmd:
                if result.success:
                    await send_reply(message, result.response)
                else:
                    await send_error(message, result.response)
            ```
        """
        if not self.is_command(message.content):
            return False, None

        cmd, args = self.parse_command(message.content)

        # Check custom commands first
        if cmd in self._custom_commands:
            try:
                result = await self._custom_commands[cmd](self, message, args)
                logger.debug("Custom command executed: %s (success=%s)", cmd, result.success)
                return True, result
            except Exception as e:
                logger.error(
                    "Error executing custom command %s: %s",
                    cmd,
                    e,
                    exc_info=True,
                )
                return True, CommandResult(
                    success=False,
                    response=f"执行命令出错: {str(e)}",
                )

        # Check built-in commands
        if cmd in self._handlers:
            try:
                result = await self._handlers[cmd](self, message, args)
                logger.debug("Built-in command executed: %s (success=%s)", cmd, result.success)
                return True, result
            except Exception as e:
                logger.error(
                    "Error executing built-in command %s: %s",
                    cmd,
                    e,
                    exc_info=True,
                )
                return True, CommandResult(
                    success=False,
                    response=f"执行命令出错: {str(e)}",
                )

        # Unknown command
        logger.debug("Unknown command: %s", cmd)
        return True, CommandResult(
            success=False,
            response=f"未知命令: {cmd}\n使用 /help 查看可用命令",
        )

    # Built-in command handlers

    async def _handle_help(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /help command - show available commands.

        Args:
            message: Incoming message
            args: Command arguments

        Returns:
            CommandResult with help text
        """
        lines = ["**可用命令:**\n"]

        # Built-in commands
        for cmd, desc in self.BUILTIN_COMMANDS.items():
            lines.append(f"  `{cmd}` - {desc}")

        # QQ-specific commands (only show on QQ platform)
        if message.platform == "qq" and self.qq_provider:
            lines.append("\n**QQ专属命令:**")
            for cmd, desc in self.QQ_COMMANDS.items():
                lines.append(f"  `{cmd}` - {desc}")

        # Custom commands
        if self._custom_commands:
            lines.append("\n**自定义命令:**")
            for cmd in sorted(self._custom_commands.keys()):
                lines.append(f"  `{cmd}`")

        # Available models
        if self.available_models:
            lines.append(f"\n**可用模型:** {', '.join(self.available_models)}")

        logger.debug("Help command executed")
        return CommandResult(success=True, response="\n".join(lines))

    async def _handle_reset(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /reset command - reset conversation context.

        Args:
            message: Incoming message
            args: Command arguments

        Returns:
            CommandResult indicating reset success
        """
        if not self.conv_manager:
            logger.warning("Conversation manager not configured for /reset command")
            return CommandResult(False, "会话管理器未配置")

        user_key = self._get_user_key(message)

        try:
            await self.conv_manager.clear_conversation(user_key)
            logger.info("Conversation reset for user: %s", user_key)
            return CommandResult(
                success=True,
                response="对话已重置，让我们重新开始吧！",
            )
        except Exception as e:
            logger.error("Failed to reset conversation for %s: %s", user_key, e)
            return CommandResult(False, f"重置对话失败: {str(e)}")

    async def _handle_history(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /history command - show conversation history summary.

        Args:
            message: Incoming message
            args: Command arguments

        Returns:
            CommandResult with conversation summary
        """
        if not self.conv_manager:
            logger.warning("Conversation manager not configured for /history command")
            return CommandResult(False, "会话管理器未配置")

        user_key = self._get_user_key(message)

        try:
            conv = await self.conv_manager.get_conversation(user_key)

            if not conv or not conv.messages:
                logger.debug("No active conversation for user: %s", user_key)
                return CommandResult(True, "当前没有活跃的对话")

            # Build summary
            msg_count = len(conv.messages)
            input_tokens = conv.input_tokens
            output_tokens = conv.output_tokens
            total_tokens = input_tokens + output_tokens

            # Calculate duration
            duration = conv.get_duration()
            duration_str = self._format_duration(duration.total_seconds())

            summary = f"""**对话统计:**
- 消息数: {msg_count}
- 输入Token: {input_tokens}
- 输出Token: {output_tokens}
- 总Token: {total_tokens}
- 会话时长: {duration_str}"""

            logger.debug("History command executed for user: %s", user_key)
            return CommandResult(success=True, response=summary)

        except Exception as e:
            logger.error("Failed to get conversation history for %s: %s", user_key, e)
            return CommandResult(False, f"获取对话历史失败: {str(e)}")

    async def _handle_model(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /model command - switch AI model.

        Args:
            message: Incoming message
            args: Command arguments (model name if switching)

        Returns:
            CommandResult with model status or switch confirmation
        """
        if not self.ai_agent:
            logger.warning("AI agent not configured for /model command")
            return CommandResult(False, "AI代理未配置")

        # If no arguments, show current model
        if not args:
            current_model = getattr(self.ai_agent, "model", "unknown")
            models_str = ", ".join(self.available_models) if self.available_models else "无"
            response = f"当前模型: {current_model}\n可用模型: {models_str}\n\n用法: /model <模型名>"
            logger.debug("Model info requested, current: %s", current_model)
            return CommandResult(success=True, response=response)

        # Switch model
        model_name = args[0]

        # Check if model is available
        if self.available_models and model_name not in self.available_models:
            logger.warning("Requested model not available: %s", model_name)
            return CommandResult(
                success=False,
                response=(
                    f"模型 '{model_name}' 不可用\n可用模型: {', '.join(self.available_models)}"
                ),
            )

        try:
            # Check if AI agent supports model switching
            if hasattr(self.ai_agent, "switch_model"):
                await self.ai_agent.switch_model(model_name)
                logger.info("Model switched to: %s", model_name)
                return CommandResult(
                    success=True,
                    response=f"已切换到模型: {model_name}",
                )
            else:
                logger.debug("AI agent does not support model switching")
                return CommandResult(
                    success=False,
                    response="AI代理不支持动态切换模型",
                )
        except Exception as e:
            logger.error("Failed to switch model to %s: %s", model_name, e)
            return CommandResult(False, f"切换模型失败: {str(e)}")

    async def _handle_persona(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        if not self.ai_agent:
            return CommandResult(False, "AI代理未配置")

        persona_manager = getattr(self.ai_agent, "persona_manager", None)
        if persona_manager is None:
            return CommandResult(False, "人格管理器未配置")

        user_key = self._get_user_key(message)

        subcommand = args[0].lower() if args else "show"

        if subcommand in {"help", "-h", "--help"}:
            return CommandResult(
                success=True,
                response=(
                    "**/persona 用法:**\n"
                    "- `/persona list` - 列出可用人格\n"
                    "- `/persona show` - 查看当前人格\n"
                    "- `/persona set <persona_id>` - 设置人格\n"
                    "- `/persona reset` - 重置为默认人格"
                ),
            )

        personas = persona_manager.personas

        if subcommand == "list":
            active_persona_id = (
                self.conversation_store.get_active_persona_id(user_key)
                if self.conversation_store is not None
                else None
            )
            effective_id = active_persona_id
            if effective_id is None or effective_id not in personas:
                effective_id = persona_manager.default_persona

            lines = ["**可用人格:**"]
            for persona_id in persona_manager.list_personas():
                persona = personas[persona_id]
                display_name = persona.display_name or persona_id
                suffix = " (当前)" if persona_id == effective_id else ""
                desc = persona.description or ""
                if desc:
                    lines.append(f"- `{persona_id}`{suffix} - {display_name}: {desc}")
                else:
                    lines.append(f"- `{persona_id}`{suffix} - {display_name}")

            return CommandResult(success=True, response="\n".join(lines))

        if subcommand == "show":
            active_persona_id = (
                self.conversation_store.get_active_persona_id(user_key)
                if self.conversation_store is not None
                else None
            )
            effective_id = active_persona_id
            if effective_id is None or effective_id not in personas:
                effective_id = persona_manager.default_persona

            if effective_id is None:
                return CommandResult(True, "当前未配置任何人格预设")

            persona = personas.get(effective_id)
            display_name = persona.display_name if persona else None
            description = persona.description if persona else None

            response = f"当前人格: `{effective_id}`"
            if display_name:
                response += f"\n名称: {display_name}"
            if description:
                response += f"\n描述: {description}"
            return CommandResult(success=True, response=response)

        if subcommand == "reset":
            if self.conversation_store is None:
                return CommandResult(False, "会话持久化未启用，无法保存人格设置")

            self.conversation_store.set_active_persona_id(
                user_key,
                None,
                platform=message.platform,
                chat_id=message.chat_id or None,
            )
            return CommandResult(success=True, response="已重置为默认人格")

        if subcommand == "set":
            if len(args) < 2:
                return CommandResult(False, "用法: /persona set <persona_id>")
            if self.conversation_store is None:
                return CommandResult(False, "会话持久化未启用，无法保存人格设置")

            persona_id = args[1]
            if persona_id not in personas:
                return CommandResult(
                    False,
                    (
                        f"未知人格: {persona_id}\n"
                        f"可用人格: {', '.join(persona_manager.list_personas())}"
                    ),
                )

            self.conversation_store.set_active_persona_id(
                user_key,
                persona_id,
                platform=message.platform,
                chat_id=message.chat_id or None,
            )
            return CommandResult(success=True, response=f"已设置人格为: {persona_id}")

        if subcommand in personas:
            if self.conversation_store is None:
                return CommandResult(False, "会话持久化未启用，无法保存人格设置")
            self.conversation_store.set_active_persona_id(
                user_key,
                subcommand,
                platform=message.platform,
                chat_id=message.chat_id or None,
            )
            return CommandResult(success=True, response=f"已设置人格为: {subcommand}")

        return CommandResult(False, "用法: /persona list|show|set|reset")

    async def _handle_stats(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /stats command - show usage statistics.

        Args:
            message: Incoming message
            args: Command arguments

        Returns:
            CommandResult with usage statistics
        """
        if not self.conv_manager:
            logger.warning("Conversation manager not configured for /stats command")
            return CommandResult(False, "会话管理器未配置")

        try:
            user_key = self._get_user_key(message)
            analytics = await self.conv_manager.get_conversation_analytics(user_key)

            msg_count = analytics.get("message_count", 0)
            total_tokens = analytics.get("total_tokens", 0)
            input_tokens = analytics.get("input_tokens", 0)
            output_tokens = analytics.get("output_tokens", 0)
            duration_minutes = analytics.get("duration_minutes", 0)

            response = f"""**使用统计:**
- 总消息数: {msg_count}
- 输入Token: {input_tokens}
- 输出Token: {output_tokens}
- 总Token数: {total_tokens}
- 对话时长: {duration_minutes:.1f} 分钟"""

            logger.debug("Stats command executed for user: %s", user_key)
            return CommandResult(success=True, response=response)

        except ValueError:
            # No conversation yet
            logger.debug("No conversation stats available")
            return CommandResult(
                success=True,
                response="还没有对话记录",
            )
        except Exception as e:
            logger.error("Failed to get statistics: %s", e)
            return CommandResult(False, f"获取统计信息失败: {str(e)}")

    async def _handle_clear(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /clear command - clear conversation context.

        Clears messages but keeps conversation record.

        Args:
            message: Incoming message
            args: Command arguments

        Returns:
            CommandResult indicating clear success
        """
        if not self.conv_manager:
            logger.warning("Conversation manager not configured for /clear command")
            return CommandResult(False, "会话管理器未配置")

        user_key = self._get_user_key(message)

        try:
            conv = await self.conv_manager.get_conversation(user_key)
            old_count = len(conv.messages)
            conv.messages.clear()
            logger.info(
                "Cleared %d messages for user: %s",
                old_count,
                user_key,
            )
            return CommandResult(
                success=True,
                response=f"已清除 {old_count} 条消息的上下文",
            )
        except Exception as e:
            logger.error("Failed to clear context for %s: %s", user_key, e)
            return CommandResult(False, f"清除上下文失败: {str(e)}")

    def _get_user_key(self, message: IncomingMessage) -> str:
        """Get user key from message for conversation tracking.

        Combines platform, chat type, and sender ID to create a unique key.

        Args:
            message: Incoming message

        Returns:
            User key string
        """
        return f"{message.platform}:{message.chat_type}:{message.sender_id}"

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{int(seconds)} 秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} 分钟"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours} 小时 {minutes} 分钟"

    # ------------------------------------------------------------------
    # QQ-specific command handlers
    # ------------------------------------------------------------------

    def _check_qq_platform(self, message: IncomingMessage) -> CommandResult | None:
        """Check if command is from QQ platform and provider is available.

        Args:
            message: Incoming message

        Returns:
            CommandResult with error if not QQ platform, None if OK
        """
        if message.platform != "qq":
            return CommandResult(False, "此命令仅在QQ平台可用")
        if not self.qq_provider:
            return CommandResult(False, "QQ提供者未配置")
        return None

    def _extract_qq_from_mentions(self, message: IncomingMessage) -> str | None:
        """Extract QQ number from message mentions.

        Args:
            message: Incoming message

        Returns:
            First mentioned QQ number or None
        """
        if message.mentions:
            return message.mentions[0]
        return None

    async def _handle_poke(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /poke command - send poke to user.

        Args:
            message: Incoming message
            args: Command arguments (optional QQ number)

        Returns:
            CommandResult with poke status
        """
        check = self._check_qq_platform(message)
        if check:
            return check

        # Get target QQ (from args or mentions)
        target_qq = args[0] if args else self._extract_qq_from_mentions(message)
        if not target_qq:
            # Poke the sender
            target_qq = message.sender_id

        try:
            target_qq_int = int(target_qq)
            group_id = int(message.chat_id) if message.chat_type == "group" else None

            result = self.qq_provider.send_poke(target_qq_int, group_id=group_id)
            if result:
                logger.info("Poke sent to %s", target_qq)
                return CommandResult(True, f"已戳 {target_qq}")
            return CommandResult(False, "戳一戳失败")
        except ValueError:
            return CommandResult(False, f"无效的QQ号: {target_qq}")
        except Exception as e:
            logger.error("Poke command failed: %s", e)
            return CommandResult(False, f"戳一戳失败: {str(e)}")

    async def _handle_mute(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /mute command - mute group member.

        Args:
            message: Incoming message
            args: [QQ号] [分钟数, 默认10分钟]

        Returns:
            CommandResult with mute status
        """
        check = self._check_qq_platform(message)
        if check:
            return check

        if message.chat_type != "group":
            return CommandResult(False, "禁言命令仅在群聊中可用")

        # Get target QQ
        target_qq = args[0] if args else self._extract_qq_from_mentions(message)
        if not target_qq:
            return CommandResult(False, "用法: /mute @用户 [分钟数]")

        # Get duration (default 10 minutes)
        duration = 10 * 60  # seconds
        if len(args) > 1:
            try:
                duration = int(args[1]) * 60
            except ValueError:
                return CommandResult(False, "无效的时长")

        try:
            target_qq_int = int(target_qq)
            group_id = int(message.chat_id)

            result = self.qq_provider.set_group_ban(group_id, target_qq_int, duration=duration)
            if result:
                minutes = duration // 60
                logger.info("Muted %s for %d minutes in group %s", target_qq, minutes, group_id)
                return CommandResult(True, f"已禁言 {target_qq} {minutes} 分钟")
            return CommandResult(False, "禁言失败，可能权限不足")
        except ValueError:
            return CommandResult(False, f"无效的QQ号: {target_qq}")
        except Exception as e:
            logger.error("Mute command failed: %s", e)
            return CommandResult(False, f"禁言失败: {str(e)}")

    async def _handle_unmute(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /unmute command - unmute group member.

        Args:
            message: Incoming message
            args: [QQ号]

        Returns:
            CommandResult with unmute status
        """
        check = self._check_qq_platform(message)
        if check:
            return check

        if message.chat_type != "group":
            return CommandResult(False, "解除禁言命令仅在群聊中可用")

        target_qq = args[0] if args else self._extract_qq_from_mentions(message)
        if not target_qq:
            return CommandResult(False, "用法: /unmute @用户")

        try:
            target_qq_int = int(target_qq)
            group_id = int(message.chat_id)

            # duration=0 means unmute
            result = self.qq_provider.set_group_ban(group_id, target_qq_int, duration=0)
            if result:
                logger.info("Unmuted %s in group %s", target_qq, group_id)
                return CommandResult(True, f"已解除 {target_qq} 的禁言")
            return CommandResult(False, "解除禁言失败，可能权限不足")
        except ValueError:
            return CommandResult(False, f"无效的QQ号: {target_qq}")
        except Exception as e:
            logger.error("Unmute command failed: %s", e)
            return CommandResult(False, f"解除禁言失败: {str(e)}")

    async def _handle_kick(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /kick command - kick group member.

        Args:
            message: Incoming message
            args: [QQ号]

        Returns:
            CommandResult with kick status
        """
        check = self._check_qq_platform(message)
        if check:
            return check

        if message.chat_type != "group":
            return CommandResult(False, "踢人命令仅在群聊中可用")

        target_qq = args[0] if args else self._extract_qq_from_mentions(message)
        if not target_qq:
            return CommandResult(False, "用法: /kick @用户")

        try:
            target_qq_int = int(target_qq)
            group_id = int(message.chat_id)

            result = self.qq_provider.set_group_kick(group_id, target_qq_int)
            if result:
                logger.info("Kicked %s from group %s", target_qq, group_id)
                return CommandResult(True, f"已将 {target_qq} 移出群聊")
            return CommandResult(False, "踢人失败，可能权限不足")
        except ValueError:
            return CommandResult(False, f"无效的QQ号: {target_qq}")
        except Exception as e:
            logger.error("Kick command failed: %s", e)
            return CommandResult(False, f"踢人失败: {str(e)}")

    async def _handle_status(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /status command - show bot online status.

        Args:
            message: Incoming message
            args: Command arguments

        Returns:
            CommandResult with bot status
        """
        check = self._check_qq_platform(message)
        if check:
            return check

        try:
            status = self.qq_provider.get_status()
            login_info = self.qq_provider.get_login_info()

            online = status.get("online", False)
            good = status.get("good", False)
            nickname = login_info.get("nickname", "未知")
            user_id = login_info.get("user_id", "未知")

            status_emoji = "🟢" if online else "🔴"
            health_emoji = "✅" if good else "⚠️"

            response = f"""**Bot状态**
{status_emoji} 在线状态: {"在线" if online else "离线"}
{health_emoji} 运行状态: {"正常" if good else "异常"}
👤 昵称: {nickname}
🆔 QQ号: {user_id}"""

            return CommandResult(True, response)
        except Exception as e:
            logger.error("Status command failed: %s", e)
            return CommandResult(False, f"获取状态失败: {str(e)}")

    async def _handle_groupinfo(self, message: IncomingMessage, args: list[str]) -> CommandResult:
        """Handle /groupinfo command - show group information.

        Args:
            message: Incoming message
            args: Command arguments

        Returns:
            CommandResult with group info
        """
        check = self._check_qq_platform(message)
        if check:
            return check

        if message.chat_type != "group":
            return CommandResult(False, "此命令仅在群聊中可用")

        try:
            group_id = int(message.chat_id)
            group_info = self.qq_provider.get_group_info(group_id)

            if not group_info:
                return CommandResult(False, "获取群信息失败")

            response = f"""**群信息**
📌 群名称: {group_info.group_name}
🆔 群号: {group_info.group_id}
👥 成员数: {group_info.member_count}/{group_info.max_member_count}"""

            return CommandResult(True, response)
        except Exception as e:
            logger.error("Groupinfo command failed: %s", e)
            return CommandResult(False, f"获取群信息失败: {str(e)}")
