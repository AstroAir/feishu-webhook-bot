"""Playwright tests for QQ extended features in WebUI."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.webui


class TestQQExtendedFeaturesController:
    """Test QQ extended features in BotController."""

    def test_qq_get_ai_characters(self, mock_bot_controller: MagicMock) -> None:
        """Test getting AI voice characters."""
        characters = mock_bot_controller.qq_get_ai_characters(123456)
        assert len(characters) == 2
        assert characters[0]["name"] == "小新"
        assert characters[1]["id"] == "char2"

    def test_qq_send_ai_voice(self, mock_bot_controller: MagicMock) -> None:
        """Test sending AI voice message."""
        result = mock_bot_controller.qq_send_ai_voice(123456, "char1", "测试文本")
        assert result is True
        mock_bot_controller.qq_send_ai_voice.assert_called_once_with(123456, "char1", "测试文本")

    def test_qq_get_group_msg_history(self, mock_bot_controller: MagicMock) -> None:
        """Test getting group message history."""
        messages = mock_bot_controller.qq_get_group_msg_history(123456, 0, 20)
        assert len(messages) == 2
        assert messages[0]["sender"]["nickname"] == "测试用户"
        assert messages[1]["message"][0]["data"]["text"] == "Hi there"

    def test_qq_get_group_notice(self, mock_bot_controller: MagicMock) -> None:
        """Test getting group announcements."""
        notices = mock_bot_controller.qq_get_group_notice(123456)
        assert len(notices) == 1
        assert "群公告测试内容" in notices[0]["content"]

    def test_qq_send_group_notice(self, mock_bot_controller: MagicMock) -> None:
        """Test sending group announcement."""
        result = mock_bot_controller.qq_send_group_notice(123456, "新公告内容")
        assert result is True

    def test_qq_ocr_image(self, mock_bot_controller: MagicMock) -> None:
        """Test OCR image recognition."""
        results = mock_bot_controller.qq_ocr_image("http://example.com/image.jpg")
        assert len(results) == 2
        assert results[0]["text"] == "识别的文字1"

    def test_qq_get_essence_msg_list(self, mock_bot_controller: MagicMock) -> None:
        """Test getting essence messages."""
        messages = mock_bot_controller.qq_get_essence_msg_list(123456)
        assert len(messages) == 1
        assert messages[0]["content"] == "精华消息1"

    def test_qq_set_essence_msg(self, mock_bot_controller: MagicMock) -> None:
        """Test setting essence message."""
        result = mock_bot_controller.qq_set_essence_msg(100)
        assert result is True

    def test_qq_delete_essence_msg(self, mock_bot_controller: MagicMock) -> None:
        """Test deleting essence message."""
        result = mock_bot_controller.qq_delete_essence_msg(100)
        assert result is True

    def test_qq_get_group_honor_info(self, mock_bot_controller: MagicMock) -> None:
        """Test getting group honor info."""
        info = mock_bot_controller.qq_get_group_honor_info(123456, "all")
        assert "talkative" in info
        assert info["talkative"]["nickname"] == "龙王"

    def test_qq_set_msg_emoji_like(self, mock_bot_controller: MagicMock) -> None:
        """Test emoji reaction."""
        result = mock_bot_controller.qq_set_msg_emoji_like(100, "128516")
        assert result is True

    def test_qq_set_group_card(self, mock_bot_controller: MagicMock) -> None:
        """Test setting member card."""
        result = mock_bot_controller.qq_set_group_card(123456, 10001, "新名片")
        assert result is True

    def test_qq_set_group_name(self, mock_bot_controller: MagicMock) -> None:
        """Test setting group name."""
        result = mock_bot_controller.qq_set_group_name(123456, "新群名")
        assert result is True

    def test_qq_set_group_special_title(self, mock_bot_controller: MagicMock) -> None:
        """Test setting special title."""
        result = mock_bot_controller.qq_set_group_special_title(123456, 10001, "特殊头衔")
        assert result is True


class TestQQExtendedFeaturesUI:
    """Test QQ extended features UI components."""

    def test_feature_card_build(self) -> None:
        """Test feature card building."""
        from feishu_webhook_bot.webui.pages.qq import _build_feature_card

        # Mock nicegui
        with patch("feishu_webhook_bot.webui.pages.qq.ui") as mock_ui:
            mock_card = MagicMock()
            mock_ui.card.return_value = mock_card
            mock_card.classes.return_value = mock_card
            mock_card.__enter__ = MagicMock(return_value=mock_card)
            mock_card.__exit__ = MagicMock(return_value=None)

            mock_column = MagicMock()
            mock_ui.column.return_value = mock_column
            mock_column.classes.return_value = mock_column
            mock_column.__enter__ = MagicMock(return_value=mock_column)
            mock_column.__exit__ = MagicMock(return_value=None)

            mock_icon = MagicMock()
            mock_ui.icon.return_value = mock_icon
            mock_icon.classes.return_value = mock_icon

            mock_label = MagicMock()
            mock_ui.label.return_value = mock_label
            mock_label.classes.return_value = mock_label

            callback = MagicMock()
            _build_feature_card("test_icon", "blue", "Test Label", callback)

            mock_ui.card.assert_called_once()
            mock_ui.icon.assert_called_once()
            mock_ui.label.assert_called_once()
            mock_card.on.assert_called_once_with("click", callback)


class TestQQGroupManagement:
    """Test QQ group management features."""

    def test_qq_get_group_list(self, mock_bot_controller: MagicMock) -> None:
        """Test getting group list."""
        groups = mock_bot_controller.qq_get_group_list()
        assert len(groups) == 2
        assert groups[0]["group_name"] == "测试群1"
        assert groups[1]["member_count"] == 50

    def test_qq_get_group_info(self, mock_bot_controller: MagicMock) -> None:
        """Test getting group info."""
        info = mock_bot_controller.qq_get_group_info(123456)
        assert info["group_name"] == "测试群"
        assert info["member_count"] == 100
        assert info["max_member_count"] == 500

    def test_qq_get_group_member_list(self, mock_bot_controller: MagicMock) -> None:
        """Test getting group member list."""
        members = mock_bot_controller.qq_get_group_member_list(123456)
        assert len(members) == 3
        assert members[0]["role"] == "owner"
        assert members[1]["card"] == "管理员"

    def test_qq_get_friend_list(self, mock_bot_controller: MagicMock) -> None:
        """Test getting friend list."""
        friends = mock_bot_controller.qq_get_friend_list()
        assert len(friends) == 2
        assert friends[0]["nickname"] == "好友1"


class TestQQBotStatus:
    """Test QQ bot status features."""

    def test_qq_get_login_info(self, mock_bot_controller: MagicMock) -> None:
        """Test getting login info."""
        info = mock_bot_controller.qq_get_login_info()
        assert info["user_id"] == 12345678
        assert info["nickname"] == "测试Bot"

    def test_qq_get_status(self, mock_bot_controller: MagicMock) -> None:
        """Test getting bot status."""
        status = mock_bot_controller.qq_get_status()
        assert status["online"] is True
        assert status["good"] is True

    def test_qq_get_version_info(self, mock_bot_controller: MagicMock) -> None:
        """Test getting version info."""
        info = mock_bot_controller.qq_get_version_info()
        assert info["app_name"] == "NapCat"
        assert info["app_version"] == "1.0.0"


class TestQQBasicFeatures:
    """Test QQ basic features."""

    def test_qq_poke(self, mock_bot_controller: MagicMock) -> None:
        """Test poke feature."""
        result = mock_bot_controller.qq_poke(10001, 123456)
        assert result is True

    def test_qq_mute(self, mock_bot_controller: MagicMock) -> None:
        """Test mute feature."""
        result = mock_bot_controller.qq_mute(123456, 10001, 600)
        assert result is True

    def test_qq_kick(self, mock_bot_controller: MagicMock) -> None:
        """Test kick feature."""
        result = mock_bot_controller.qq_kick(123456, 10001, False)
        assert result is True

    def test_qq_send_message(self, mock_bot_controller: MagicMock) -> None:
        """Test send message."""
        result = mock_bot_controller.qq_send_message("Hello", "group:123456")
        assert result is True

    def test_qq_send_image(self, mock_bot_controller: MagicMock) -> None:
        """Test send image."""
        result = mock_bot_controller.qq_send_image("http://example.com/img.jpg", "group:123456")
        assert result is True

    def test_qq_set_group_whole_ban(self, mock_bot_controller: MagicMock) -> None:
        """Test whole group ban."""
        result = mock_bot_controller.qq_set_group_whole_ban(123456, True)
        assert result is True

    def test_qq_set_group_admin(self, mock_bot_controller: MagicMock) -> None:
        """Test set group admin."""
        result = mock_bot_controller.qq_set_group_admin(123456, 10001, True)
        assert result is True
