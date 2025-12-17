"""Tests for chat controller message routing and replies."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from feishu_webhook_bot.ai.commands import CommandResult
from feishu_webhook_bot.chat.controller import ChatConfig, ChatController
from feishu_webhook_bot.core.message_handler import IncomingMessage
from feishu_webhook_bot.core.provider import SendResult


class StubProvider:
    """Simple provider stub capturing sent messages."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_text(self, text: str, target: str) -> SendResult:
        self.sent.append((text, target))
        return SendResult.ok("msg_1")


class StubCommandHandler:
    """Command handler stub returning fixed response."""

    def __init__(self, response: str) -> None:
        self.called = False
        self.response = response
        self.conversation_store = None

    async def process(self, message: IncomingMessage):
        self.called = True
        return True, CommandResult(success=True, response=self.response)


class StubAIAgent:
    """AI agent stub capturing chat calls."""

    def __init__(self, reply: str):
        self.reply = reply
        self.calls: list[tuple[str, str]] = []
        self.conversation_store = None

    def set_conversation_store(self, conversation_store) -> None:
        self.conversation_store = conversation_store

    async def chat(self, user_key: str, content: str) -> str:
        self.calls.append((user_key, content))
        return self.reply


@pytest.mark.anyio
async def test_middleware_can_stop_processing():
    controller = ChatController()
    controller._process_message = AsyncMock()

    @controller.middleware
    async def stop(_ctx):
        return False

    message = IncomingMessage(
        id="1",
        platform="feishu",
        chat_type="private",
        chat_id="",
        sender_id="user",
        sender_name="User",
        content="hello",
    )

    await controller.handle_incoming(message)

    controller._process_message.assert_not_awaited()


@pytest.mark.anyio
async def test_command_handler_response_sent():
    provider = StubProvider()
    handler = StubCommandHandler(response="pong")
    controller = ChatController(
        command_handler=handler,
        providers={"feishu": provider},
        config=ChatConfig(command_prefix="/"),
    )

    message = IncomingMessage(
        id="cmd1",
        platform="feishu",
        chat_type="private",
        chat_id="",
        sender_id="u1",
        sender_name="User",
        content="/ping",
    )

    await controller.handle_incoming(message)

    assert handler.called is True
    # When chat_id is empty, sender_id is used as fallback target
    assert provider.sent == [("pong", "u1")]


@pytest.mark.anyio
async def test_ai_response_truncated_and_sent():
    provider = StubProvider()
    ai_agent = StubAIAgent(reply="123456789012345")
    controller = ChatController(
        ai_agent=ai_agent,
        providers={"feishu": provider},
        config=ChatConfig(max_message_length=10),
    )

    message = IncomingMessage(
        id="ai1",
        platform="feishu",
        chat_type="private",
        chat_id="",
        sender_id="u2",
        sender_name="User",
        content="hello",
    )

    await controller.handle_incoming(message)

    assert ai_agent.calls == [("feishu:private:u2", "hello")]
    assert provider.sent[0][0] == "1234567..."


@pytest.mark.anyio
async def test_broadcast_sends_to_multiple_targets():
    provider = StubProvider()
    controller = ChatController(providers={"feishu": provider})

    results = await controller.broadcast(
        "announcement",
        platforms=["feishu"],
        targets={"feishu": ["t1", "t2"]},
    )

    assert provider.sent == [("announcement", "t1"), ("announcement", "t2")]
    assert list(results.keys()) == ["feishu"]
    assert all(r.success for r in results["feishu"])


def test_conversation_store_injected_into_components():
    store = object()
    ai_agent = StubAIAgent(reply="ok")
    handler = StubCommandHandler(response="pong")

    controller = ChatController(
        ai_agent=ai_agent,
        command_handler=handler,
        conversation_store=store,
    )

    assert controller.conversation_store is store
    assert ai_agent.conversation_store is store
    assert handler.conversation_store is store
