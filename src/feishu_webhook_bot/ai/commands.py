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
        "/stats": "显示使用统计",
        "/clear": "清除当前会话的上下文",
    }

    def __init__(
        self,
        ai_agent: AIAgent | None = None,
        conversation_manager: ConversationManager | None = None,
        command_prefix: str = "/",
        available_models: list[str] | None = None,
    ) -> None:
        """Initialize command handler.

        Args:
            ai_agent: AI agent instance for model-related operations
            conversation_manager: Conversation manager instance for conversation operations
            command_prefix: Prefix for commands (default: "/")
            available_models: List of models available for switching
        """
        self.ai_agent = ai_agent
        self.conv_manager = conversation_manager
        self.prefix = command_prefix
        self.available_models = available_models or []
        self._custom_commands: dict[str, CommandFunc] = {}

        # Register built-in handlers
        self._handlers: dict[str, CommandFunc] = {
            "/help": self._handle_help,
            "/reset": self._handle_reset,
            "/history": self._handle_history,
            "/model": self._handle_model,
            "/stats": self._handle_stats,
            "/clear": self._handle_clear,
        }

        logger.debug(
            "CommandHandler initialized with prefix='%s', models=%s",
            self.prefix,
            self.available_models,
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
                raise ValueError(
                    f"Command '{name}' must start with prefix '{self.prefix}'"
                )

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

    async def _handle_help(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
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

    async def _handle_reset(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
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

    async def _handle_history(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
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

    async def _handle_model(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
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
            response = (
                f"当前模型: {current_model}\n可用模型: {models_str}\n\n用法: /model <模型名>"
            )
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
                    f"模型 '{model_name}' 不可用\n"
                    f"可用模型: {', '.join(self.available_models)}"
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

    async def _handle_stats(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
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

    async def _handle_clear(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
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
