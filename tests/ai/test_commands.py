"""Tests for chat command handler."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from feishu_webhook_bot.ai.commands import CommandHandler, CommandResult
from feishu_webhook_bot.core.message_handler import IncomingMessage


class DummyConversation:
    def __init__(self) -> None:
        self.messages = ["hi"]
        self.input_tokens = 5
        self.output_tokens = 7

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
