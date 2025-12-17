#!/usr/bin/env python3
"""Conversation Manager Example."""

import asyncio

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging

setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)

try:
    from feishu_webhook_bot.ai import ConversationManager, ConversationState

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("AI dependencies not available.")


def demo_basic_conversation_state():
    print("\n" + "=" * 60)
    print("Demo 1: Basic Conversation State")
    print("=" * 60)
    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    user_id = "user_123"
    state = ConversationState(user_id)
    print(f"Created conversation state for: {user_id}")
    print(f"  Created at: {state.created_at}")
    print(f"  Message count: {state.message_count}")
    state.context["user_name"] = "Alice"
    print(f"  Context: {state.context}")


async def demo_conversation_manager():
    print("\n" + "=" * 60)
    print("Demo 2: Conversation Manager")
    print("=" * 60)
    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    manager = ConversationManager(timeout_minutes=30, cleanup_interval_seconds=300)
    print("ConversationManager created:")
    print("  Timeout: 30 minutes")
    print("  Cleanup interval: 300 seconds")

    user_id = "user_456"
    conversation = await manager.get_conversation(user_id)
    print(f"\nConversation for {user_id}:")
    print(f"  Message count: {conversation.message_count}")


async def demo_multi_turn():
    print("\n" + "=" * 60)
    print("Demo 3: Multi-Turn Dialogue")
    print("=" * 60)
    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    manager = ConversationManager()
    user_id = "user_789"
    conversation = await manager.get_conversation(user_id)

    turns = [
        ("Hello", "Hi there!"),
        ("How are you?", "I'm doing well!"),
    ]

    print("Simulating dialogue:")
    for user_msg, assistant_msg in turns:
        print(f"  User: {user_msg}")
        print(f"  Assistant: {assistant_msg}")
        conversation.input_tokens += len(user_msg.split()) * 2
        conversation.output_tokens += len(assistant_msg.split()) * 2
        conversation.message_count += 2

    total = conversation.input_tokens + conversation.output_tokens
    print(f"\nTotal tokens: {total}")


def main():
    print("=" * 60)
    print("Conversation Manager Examples")
    print("=" * 60)

    demo_basic_conversation_state()
    asyncio.run(demo_conversation_manager())
    asyncio.run(demo_multi_turn())

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
