"""Pytest fixtures for WebUI Playwright tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_bot_controller() -> MagicMock:
    """Create a mock BotController for testing."""
    controller = MagicMock()

    # QQ provider methods
    controller.get_qq_provider.return_value = MagicMock()
    controller.get_message_provider_list.return_value = [
        {
            "name": "test_qq",
            "provider_type": "napcat",
            "connected": True,
            "enabled": True,
        }
    ]

    # QQ extended features
    controller.qq_get_ai_characters.return_value = [
        {"id": "char1", "name": "小新"},
        {"id": "char2", "name": "小爱"},
    ]
    controller.qq_send_ai_voice.return_value = True
    controller.qq_get_group_msg_history.return_value = [
        {
            "message_id": 123,
            "sender": {"user_id": 10001, "nickname": "测试用户"},
            "message": [{"type": "text", "data": {"text": "Hello World"}}],
        },
        {
            "message_id": 124,
            "sender": {"user_id": 10002, "nickname": "用户2"},
            "message": [{"type": "text", "data": {"text": "Hi there"}}],
        },
    ]
    controller.qq_get_group_notice.return_value = [
        {"content": "群公告测试内容", "sender_id": 10001},
    ]
    controller.qq_send_group_notice.return_value = True
    controller.qq_ocr_image.return_value = [
        {"text": "识别的文字1"},
        {"text": "识别的文字2"},
    ]
    controller.qq_get_group_list.return_value = [
        {"group_id": 123456, "group_name": "测试群1", "member_count": 100},
        {"group_id": 789012, "group_name": "测试群2", "member_count": 50},
    ]
    controller.qq_get_friend_list.return_value = [
        {"user_id": 10001, "nickname": "好友1"},
        {"user_id": 10002, "nickname": "好友2"},
    ]
    controller.qq_get_group_member_list.return_value = [
        {"user_id": 10001, "nickname": "成员1", "role": "owner", "card": ""},
        {"user_id": 10002, "nickname": "成员2", "role": "admin", "card": "管理员"},
        {"user_id": 10003, "nickname": "成员3", "role": "member", "card": ""},
    ]
    controller.qq_get_group_info.return_value = {
        "group_id": 123456,
        "group_name": "测试群",
        "member_count": 100,
        "max_member_count": 500,
    }
    controller.qq_get_login_info.return_value = {
        "user_id": 12345678,
        "nickname": "测试Bot",
    }
    controller.qq_get_status.return_value = {
        "online": True,
        "good": True,
    }
    controller.qq_get_version_info.return_value = {
        "app_name": "NapCat",
        "app_version": "1.0.0",
        "protocol_version": "v11",
    }
    controller.qq_poke.return_value = True
    controller.qq_mute.return_value = True
    controller.qq_kick.return_value = True
    controller.qq_send_message.return_value = True
    controller.qq_send_image.return_value = True

    # Essence messages
    controller.qq_get_essence_msg_list.return_value = [
        {"message_id": 100, "sender_nick": "用户1", "content": "精华消息1"},
    ]
    controller.qq_set_essence_msg.return_value = True
    controller.qq_delete_essence_msg.return_value = True

    # Group honor
    controller.qq_get_group_honor_info.return_value = {
        "talkative": {"user_id": 10001, "nickname": "龙王"},
    }

    # Emoji reaction
    controller.qq_set_msg_emoji_like.return_value = True

    # Group management
    controller.qq_set_group_card.return_value = True
    controller.qq_set_group_name.return_value = True
    controller.qq_set_group_special_title.return_value = True
    controller.qq_set_group_whole_ban.return_value = True
    controller.qq_set_group_admin.return_value = True

    return controller


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock config for testing."""
    config = MagicMock()
    config.providers = []
    config.bot = MagicMock()
    config.bot.name = "Test Bot"
    return config
