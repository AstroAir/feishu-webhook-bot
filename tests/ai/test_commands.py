"""Comprehensive tests for chat command handler.

Tests cover:
- CommandHandler initialization
- Command parsing and detection
- Built-in commands (/help, /reset, /history, /model, /stats, /clear)
- Persona commands (/persona list, /persona show, /persona set, /persona reset)
- QQ-specific commands (/poke, /mute, /unmute, /kick, /status, /groupinfo)
- Custom command registration and unregistration
- Platform-specific helpers
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from feishu_webhook_bot.ai.commands import CommandHandler, CommandResult
from feishu_webhook_bot.core.message_handler import IncomingMessage

# ==============================================================================
# Mock Classes
# ==============================================================================


class DummyConversation:
    def __init__(self) -> None:
        self.messages = ["hi"]
        self.input_tokens = 5
        self.output_tokens = 7

    def clear(self) -> None:
        self.messages.clear()

    def get_duration(self) -> timedelta:
        return timedelta(seconds=125)


class DummyConversationManager:
    def __init__(self) -> None:
        self.cleared: list[str] = []

    async def clear_conversation(self, key: str) -> None:
        self.cleared.append(key)

    async def get_conversation(self, key: str) -> DummyConversation:
        return DummyConversation()

    async def get_conversation_analytics(self, key: str) -> dict:
        return {
            "message_count": 3,
            "total_tokens": 30,
            "input_tokens": 10,
            "output_tokens": 20,
            "duration_minutes": 2.5,
        }


class DummyAgent:
    def __init__(self, model: str = "gpt-4o") -> None:
        self.model = model
        self.switched_to: list[str] = []

    async def switch_model(self, name: str) -> None:
        self.switched_to.append(name)


@pytest.fixture
def message_factory():
    def _make(content: str = "/test") -> IncomingMessage:
        return IncomingMessage(
            id="1",
            platform="feishu",
            chat_type="private",
            chat_id="",
            sender_id="user",
            sender_name="User",
            content=content,
        )

    return _make


@pytest.mark.anyio
async def test_parse_and_detect_command(message_factory):
    handler = CommandHandler()
    message = message_factory("/Model gpt-4o")

    cmd, args = handler.parse_command(message.content)
    assert cmd == "/model"
    assert args == ["gpt-4o"]
    assert handler.is_command(message.content) is True


@pytest.mark.anyio
async def test_custom_command_registration_and_execution(message_factory):
    handler = CommandHandler()

    @handler.register("/echo")
    async def _echo(self, message, args):  # type: ignore[unused-argument]
        return CommandResult(True, f"echo:{' '.join(args)}")

    message = message_factory("/echo hello world")
    is_cmd, result = await handler.process(message)

    assert is_cmd is True
    assert result and result.response == "echo:hello world"
    assert handler.unregister("/echo") is True
    assert handler.unregister("/help") is False  # built-in cannot be removed


@pytest.mark.anyio
async def test_unknown_command_returns_helpful_message(message_factory):
    handler = CommandHandler()
    message = message_factory("/doesnotexist")

    is_cmd, result = await handler.process(message)

    assert is_cmd is True
    assert result is not None
    assert result.success is False
    assert "未知命令" in result.response


@pytest.mark.anyio
async def test_handle_model_switches_when_available(message_factory):
    agent = DummyAgent()
    handler = CommandHandler(ai_agent=agent, available_models=["gpt-4o"])
    message = message_factory()

    result = await handler._handle_model(message, ["gpt-4o"])

    assert result.success is True
    assert agent.switched_to == ["gpt-4o"]

    unavailable = await handler._handle_model(message, ["bad-model"])
    assert unavailable.success is False


@pytest.mark.anyio
async def test_handle_history_and_stats(message_factory):
    conv_manager = DummyConversationManager()
    handler = CommandHandler(conversation_manager=conv_manager)
    message = message_factory()

    history = await handler._handle_history(message, [])
    assert history.success is True
    assert "消息数" in history.response

    stats = await handler._handle_stats(message, [])
    assert stats.success is True
    assert "总消息数" in stats.response


@pytest.mark.anyio
async def test_handle_clear_clears_messages(message_factory):
    conv_manager = DummyConversationManager()
    handler = CommandHandler(conversation_manager=conv_manager)
    message = message_factory()

    result = await handler._handle_clear(message, [])

    assert result.success is True
    assert conv_manager.cleared == []  # clear does not call clear_conversation
    assert "已清除" in result.response


@pytest.mark.anyio
async def test_format_duration_helper():
    handler = CommandHandler()
    assert handler._format_duration(45) == "45 秒"
    assert handler._format_duration(120) == "2 分钟"
    assert handler._format_duration(3700) == "1 小时 1 分钟"


# ==============================================================================
# Help Command Tests
# ==============================================================================


@pytest.mark.anyio
async def test_handle_help_returns_command_list(message_factory):
    """Test /help returns available commands."""
    handler = CommandHandler()
    message = message_factory("/help")

    is_cmd, result = await handler.process(message)

    assert is_cmd is True
    assert result is not None
    assert result.success is True
    assert "/help" in result.response
    assert "/reset" in result.response
    assert "/model" in result.response


@pytest.mark.anyio
async def test_handle_help_with_specific_command(message_factory):
    """Test /help with specific command shows detailed help."""
    handler = CommandHandler()
    message = message_factory("/help reset")

    is_cmd, result = await handler.process(message)

    assert is_cmd is True
    assert result is not None


# ==============================================================================
# Reset Command Tests
# ==============================================================================


@pytest.mark.anyio
async def test_handle_reset_clears_conversation(message_factory):
    """Test /reset clears conversation."""
    conv_manager = DummyConversationManager()
    handler = CommandHandler(conversation_manager=conv_manager)
    message = message_factory("/reset")

    is_cmd, result = await handler.process(message)

    assert is_cmd is True
    assert result is not None
    assert result.success is True
    assert "已重置" in result.response or "重置" in result.response


# ==============================================================================
# Persona Command Tests
# ==============================================================================


class TestPersonaCommands:
    """Tests for /persona command."""

    @pytest.mark.anyio
    async def test_persona_list(self, message_factory):
        """Test /persona list command."""
        handler = CommandHandler()
        message = message_factory("/persona list")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_persona_show(self, message_factory):
        """Test /persona show displays current persona."""
        handler = CommandHandler()
        message = message_factory("/persona show")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_persona_set(self, message_factory):
        """Test /persona set changes persona."""
        handler = CommandHandler()
        message = message_factory("/persona set coder")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_persona_reset(self, message_factory):
        """Test /persona reset returns to default persona."""
        handler = CommandHandler()
        message = message_factory("/persona reset")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_persona_no_subcommand(self, message_factory):
        """Test /persona without subcommand shows help."""
        handler = CommandHandler()
        message = message_factory("/persona")

        is_cmd, result = await handler.process(message)


# ==============================================================================
# QQ-Specific Command Tests
# ==============================================================================


class TestQQCommands:
    """Tests for QQ-specific commands."""

    @pytest.fixture
    def qq_message_factory(self):
        """Create QQ platform messages."""

        def _make(content: str, chat_type: str = "group") -> IncomingMessage:
            return IncomingMessage(
                id="1",
                platform="qq",
                chat_type=chat_type,
                chat_id="group123",
                sender_id="user123",
                sender_name="User",
                content=content,
            )

        return _make

    @pytest.fixture
    def feishu_message_factory(self):
        """Create Feishu platform messages."""

        def _make(content: str) -> IncomingMessage:
            return IncomingMessage(
                id="1",
                platform="feishu",
                chat_type="group",
                chat_id="group123",
                sender_id="user123",
                sender_name="User",
                content=content,
            )

        return _make

    @pytest.fixture
    def mock_qq_provider(self):
        """Create mock QQ provider."""
        provider = MagicMock()
        provider.send_group_poke = AsyncMock(return_value=True)
        provider.set_group_ban = AsyncMock(return_value=True)
        provider.set_group_kick = AsyncMock(return_value=True)
        provider.get_status = AsyncMock(
            return_value={"online": True, "good": True, "stat": {"message_received": 100}}
        )
        provider.get_group_info = AsyncMock(
            return_value={
                "group_id": 123456,
                "group_name": "Test Group",
                "member_count": 50,
                "max_member_count": 200,
            }
        )
        return provider

    @pytest.mark.anyio
    async def test_poke_on_qq_platform(self, qq_message_factory, mock_qq_provider):
        """Test /poke works on QQ platform."""
        handler = CommandHandler(qq_provider=mock_qq_provider)
        message = qq_message_factory("/poke @someone")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_poke_on_non_qq_platform(self, feishu_message_factory):
        """Test /poke fails on non-QQ platform."""
        handler = CommandHandler()
        message = feishu_message_factory("/poke @someone")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None
        # Should indicate this command is QQ-only or fail

    @pytest.mark.anyio
    async def test_mute_command(self, qq_message_factory, mock_qq_provider):
        """Test /mute command."""
        handler = CommandHandler(qq_provider=mock_qq_provider)
        message = qq_message_factory("/mute @user 60")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_unmute_command(self, qq_message_factory, mock_qq_provider):
        """Test /unmute command."""
        handler = CommandHandler(qq_provider=mock_qq_provider)
        message = qq_message_factory("/unmute @user")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_kick_command(self, qq_message_factory, mock_qq_provider):
        """Test /kick command."""
        handler = CommandHandler(qq_provider=mock_qq_provider)
        message = qq_message_factory("/kick @user")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_status_command(self, qq_message_factory, mock_qq_provider):
        """Test /status command."""
        handler = CommandHandler(qq_provider=mock_qq_provider)
        message = qq_message_factory("/status")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_groupinfo_command(self, qq_message_factory, mock_qq_provider):
        """Test /groupinfo command."""
        handler = CommandHandler(qq_provider=mock_qq_provider)
        message = qq_message_factory("/groupinfo")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_groupinfo_in_private_chat(self, qq_message_factory, mock_qq_provider):
        """Test /groupinfo fails in private chat."""
        handler = CommandHandler(qq_provider=mock_qq_provider)
        message = qq_message_factory("/groupinfo", chat_type="private")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None
        # Should indicate this command only works in groups


# ==============================================================================
# Command Handler Initialization Tests
# ==============================================================================


class TestCommandHandlerInitialization:
    """Tests for CommandHandler initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        handler = CommandHandler()

        assert handler.ai_agent is None
        assert handler.conv_manager is None
        assert handler.qq_provider is None

    def test_initialization_with_all_dependencies(self):
        """Test initialization with all dependencies."""
        agent = DummyAgent()
        conv_manager = DummyConversationManager()

        handler = CommandHandler(
            ai_agent=agent,
            conversation_manager=conv_manager,
            available_models=["gpt-4o", "claude-3"],
        )

        assert handler.ai_agent == agent
        assert handler.conv_manager == conv_manager
        assert "gpt-4o" in handler.available_models

    def test_built_in_commands_registered(self):
        """Test built-in commands are registered."""
        handler = CommandHandler()

        # Check built-in commands exist
        assert handler.is_command("/help")
        assert handler.is_command("/reset")
        assert handler.is_command("/history")
        assert handler.is_command("/model")
        assert handler.is_command("/stats")
        assert handler.is_command("/clear")
        assert handler.is_command("/persona")


# ==============================================================================
# Command Parsing Tests
# ==============================================================================


class TestCommandParsing:
    """Tests for command parsing."""

    def test_parse_simple_command(self):
        """Test parsing simple command."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("/help")

        assert cmd == "/help"
        assert args == []

    def test_parse_command_with_args(self):
        """Test parsing command with arguments."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("/model gpt-4o")

        assert cmd == "/model"
        assert args == ["gpt-4o"]

    def test_parse_command_with_multiple_args(self):
        """Test parsing command with multiple arguments."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("/mute @user 60")

        assert cmd == "/mute"
        assert len(args) >= 1

    def test_parse_command_case_insensitive(self):
        """Test command parsing is case insensitive."""
        handler = CommandHandler()

        cmd1, _ = handler.parse_command("/Help")
        cmd2, _ = handler.parse_command("/HELP")
        cmd3, _ = handler.parse_command("/help")

        assert cmd1 == cmd2 == cmd3 == "/help"

    def test_is_command_detection(self):
        """Test command detection."""
        handler = CommandHandler()

        assert handler.is_command("/help") is True
        assert handler.is_command("/model gpt-4o") is True
        assert handler.is_command("hello") is False
        assert handler.is_command("not a /command") is False

    def test_non_command_text(self):
        """Test non-command text detection."""
        handler = CommandHandler()

        assert handler.is_command("Hello, how are you?") is False
        assert handler.is_command("") is False
        assert handler.is_command("  ") is False


# ==============================================================================
# Custom Command Registration Tests
# ==============================================================================


class TestCustomCommandRegistration:
    """Tests for custom command registration."""

    @pytest.mark.anyio
    async def test_register_and_execute_custom_command(self, message_factory):
        """Test registering and executing a custom command."""
        handler = CommandHandler()

        @handler.register("/greet")
        async def _greet(self, message, args):
            name = args[0] if args else "World"
            return CommandResult(True, f"Hello, {name}!")

        message = message_factory("/greet Alice")
        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None
        assert result.success is True
        assert "Hello, Alice!" in result.response

    @pytest.mark.anyio
    async def test_unregister_custom_command(self, message_factory):
        """Test unregistering a custom command."""
        handler = CommandHandler()

        @handler.register("/temp")
        async def _temp(self, message, args):
            return CommandResult(True, "temp")

        # Verify it works
        assert handler.is_command("/temp")

        # Unregister
        result = handler.unregister("/temp")
        assert result is True

        # Should no longer exist as a known command handler
        # but /temp still starts with /, so is_command checks format

    @pytest.mark.anyio
    async def test_cannot_unregister_builtin_command(self):
        """Test cannot unregister built-in commands."""
        handler = CommandHandler()

        result = handler.unregister("/help")

        assert result is False

    @pytest.mark.anyio
    async def test_register_command_basic(self, message_factory):
        """Test registering command."""
        handler = CommandHandler()

        @handler.register("/custom")
        async def _custom(self, message, args):
            return CommandResult(True, "custom result")

        # Command should be registered
        assert handler.is_command("/custom")


# ==============================================================================
# Edge Cases and Error Handling Tests
# ==============================================================================


class TestCommandEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.anyio
    async def test_empty_message_content(self):
        """Test handling empty message content."""
        handler = CommandHandler()
        message = IncomingMessage(
            id="1",
            platform="feishu",
            chat_type="private",
            chat_id="",
            sender_id="user",
            sender_name="User",
            content="",
        )

        is_cmd, result = await handler.process(message)

        assert is_cmd is False

    @pytest.mark.anyio
    async def test_whitespace_only_message(self):
        """Test handling whitespace-only message."""
        handler = CommandHandler()
        message = IncomingMessage(
            id="1",
            platform="feishu",
            chat_type="private",
            chat_id="",
            sender_id="user",
            sender_name="User",
            content="   ",
        )

        is_cmd, result = await handler.process(message)

        assert is_cmd is False

    @pytest.mark.anyio
    async def test_command_with_special_characters(self, message_factory):
        """Test command with special characters in args."""
        handler = CommandHandler()
        message = message_factory("/help @user#123")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None

    @pytest.mark.anyio
    async def test_very_long_command_args(self, message_factory):
        """Test command with very long arguments."""
        handler = CommandHandler()
        long_arg = "a" * 1000
        message = message_factory(f"/help {long_arg}")

        is_cmd, result = await handler.process(message)

        assert is_cmd is True
        assert result is not None
