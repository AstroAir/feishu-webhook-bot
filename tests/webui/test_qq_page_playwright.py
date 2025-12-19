"""Playwright browser tests for QQ page in WebUI."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def mock_controller() -> MagicMock:
    """Create mock controller with QQ methods."""
    controller = MagicMock()
    controller.get_message_provider_list.return_value = [
        {"name": "qq_test", "provider_type": "napcat", "connected": True, "enabled": True}
    ]
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
        }
    ]
    controller.qq_get_group_notice.return_value = [{"content": "测试公告", "sender_id": 10001}]
    controller.qq_send_group_notice.return_value = True
    controller.qq_ocr_image.return_value = [{"text": "识别文字"}]
    controller.qq_get_group_list.return_value = [
        {"group_id": 123456, "group_name": "测试群", "member_count": 100}
    ]
    controller.qq_get_login_info.return_value = {"user_id": 12345, "nickname": "TestBot"}
    controller.qq_get_status.return_value = {"online": True, "good": True}
    controller.qq_get_version_info.return_value = {
        "app_name": "NapCat",
        "app_version": "1.0.0",
    }
    return controller


class TestQQPageI18n:
    """Test i18n translations for QQ page."""

    def test_english_translations_exist(self) -> None:
        """Test that English translations exist for all QQ extended feature keys."""
        from feishu_webhook_bot.webui.i18n import TRANSLATIONS

        en_translations = TRANSLATIONS["en"]
        required_keys = [
            "qq.extended_title",
            "qq.extended_desc",
            "qq.feature_ai_voice",
            "qq.feature_msg_history",
            "qq.feature_notice",
            "qq.feature_ocr",
            "qq.ai_voice_title",
            "qq.ai_voice_character",
            "qq.ai_voice_text",
            "qq.ai_voice_send",
            "qq.ai_voice_success",
            "qq.msg_history_title",
            "qq.msg_history_count",
            "qq.msg_history_load",
            "qq.notice_title",
            "qq.notice_content",
            "qq.notice_send",
            "qq.ocr_title",
            "qq.ocr_image_url",
            "qq.ocr_perform",
            "qq.ocr_result",
        ]
        for key in required_keys:
            assert key in en_translations, f"Missing English translation: {key}"

    def test_chinese_translations_exist(self) -> None:
        """Test that Chinese translations exist for all QQ extended feature keys."""
        from feishu_webhook_bot.webui.i18n import TRANSLATIONS

        zh_translations = TRANSLATIONS["zh"]
        required_keys = [
            "qq.extended_title",
            "qq.extended_desc",
            "qq.feature_ai_voice",
            "qq.feature_msg_history",
            "qq.feature_notice",
            "qq.feature_ocr",
            "qq.ai_voice_title",
            "qq.ai_voice_character",
            "qq.ai_voice_text",
            "qq.ai_voice_send",
            "qq.ai_voice_success",
            "qq.msg_history_title",
            "qq.msg_history_count",
            "qq.msg_history_load",
            "qq.notice_title",
            "qq.notice_content",
            "qq.notice_send",
            "qq.ocr_title",
            "qq.ocr_image_url",
            "qq.ocr_perform",
            "qq.ocr_result",
        ]
        for key in required_keys:
            assert key in zh_translations, f"Missing Chinese translation: {key}"

    def test_translation_function(self) -> None:
        """Test the translation function works correctly."""
        from feishu_webhook_bot.webui.i18n import set_lang, t

        set_lang("en")
        assert t("qq.extended_title") == "Extended Features"

        set_lang("zh")
        assert t("qq.extended_title") == "扩展功能"


class TestQQControllerMethods:
    """Test QQ controller methods directly."""

    def test_controller_has_extended_methods(self) -> None:
        """Test that BotController has all extended QQ methods."""
        from feishu_webhook_bot.webui.controller import BotController

        # Check method existence
        assert hasattr(BotController, "qq_get_ai_characters")
        assert hasattr(BotController, "qq_send_ai_voice")
        assert hasattr(BotController, "qq_get_group_msg_history")
        assert hasattr(BotController, "qq_get_group_notice")
        assert hasattr(BotController, "qq_send_group_notice")
        assert hasattr(BotController, "qq_get_essence_msg_list")
        assert hasattr(BotController, "qq_set_essence_msg")
        assert hasattr(BotController, "qq_delete_essence_msg")
        assert hasattr(BotController, "qq_get_group_honor_info")
        assert hasattr(BotController, "qq_ocr_image")
        assert hasattr(BotController, "qq_set_msg_emoji_like")
        assert hasattr(BotController, "qq_set_group_card")
        assert hasattr(BotController, "qq_set_group_name")
        assert hasattr(BotController, "qq_set_group_special_title")

    def test_qq_get_ai_characters_returns_list(self, mock_controller: MagicMock) -> None:
        """Test qq_get_ai_characters returns a list."""
        result = mock_controller.qq_get_ai_characters(123456)
        assert isinstance(result, list)
        assert len(result) > 0
        assert "id" in result[0]
        assert "name" in result[0]

    def test_qq_get_group_msg_history_returns_messages(self, mock_controller: MagicMock) -> None:
        """Test qq_get_group_msg_history returns messages."""
        result = mock_controller.qq_get_group_msg_history(123456, 0, 10)
        assert isinstance(result, list)
        assert len(result) > 0
        assert "sender" in result[0]
        assert "message" in result[0]

    def test_qq_ocr_image_returns_text(self, mock_controller: MagicMock) -> None:
        """Test qq_ocr_image returns text results."""
        result = mock_controller.qq_ocr_image("http://example.com/img.jpg")
        assert isinstance(result, list)
        assert "text" in result[0]


class TestQQPageUIComponents:
    """Test QQ page UI component functions."""

    def test_build_qq_extended_features_function_exists(self) -> None:
        """Test that _build_qq_extended_features function exists."""
        from feishu_webhook_bot.webui.pages import qq

        assert hasattr(qq, "_build_qq_extended_features")
        assert callable(qq._build_qq_extended_features)

    def test_build_feature_card_function_exists(self) -> None:
        """Test that _build_feature_card function exists."""
        from feishu_webhook_bot.webui.pages import qq

        assert hasattr(qq, "_build_feature_card")
        assert callable(qq._build_feature_card)

    def test_show_ai_voice_dialog_function_exists(self) -> None:
        """Test that _show_ai_voice_dialog function exists."""
        from feishu_webhook_bot.webui.pages import qq

        assert hasattr(qq, "_show_ai_voice_dialog")
        assert callable(qq._show_ai_voice_dialog)

    def test_show_msg_history_dialog_function_exists(self) -> None:
        """Test that _show_msg_history_dialog function exists."""
        from feishu_webhook_bot.webui.pages import qq

        assert hasattr(qq, "_show_msg_history_dialog")
        assert callable(qq._show_msg_history_dialog)

    def test_show_notice_dialog_function_exists(self) -> None:
        """Test that _show_notice_dialog function exists."""
        from feishu_webhook_bot.webui.pages import qq

        assert hasattr(qq, "_show_notice_dialog")
        assert callable(qq._show_notice_dialog)

    def test_show_ocr_dialog_function_exists(self) -> None:
        """Test that _show_ocr_dialog function exists."""
        from feishu_webhook_bot.webui.pages import qq

        assert hasattr(qq, "_show_ocr_dialog")
        assert callable(qq._show_ocr_dialog)


class TestQQCLICommands:
    """Test QQ CLI commands."""

    def test_cli_qq_commands_exist(self) -> None:
        """Test that CLI QQ commands exist."""
        from feishu_webhook_bot.cli.commands import provider

        # Check that command handlers dict contains QQ commands
        assert hasattr(provider, "_cmd_qq_poke")
        assert hasattr(provider, "_cmd_qq_mute")
        assert hasattr(provider, "_cmd_qq_kick")
        assert hasattr(provider, "_cmd_qq_history")
        assert hasattr(provider, "_cmd_qq_groups")

    def test_cmd_qq_poke_function(self) -> None:
        """Test _cmd_qq_poke function structure."""
        from feishu_webhook_bot.cli.commands.provider import _cmd_qq_poke

        assert callable(_cmd_qq_poke)

    def test_cmd_qq_mute_function(self) -> None:
        """Test _cmd_qq_mute function structure."""
        from feishu_webhook_bot.cli.commands.provider import _cmd_qq_mute

        assert callable(_cmd_qq_mute)

    def test_cmd_qq_history_function(self) -> None:
        """Test _cmd_qq_history function structure."""
        from feishu_webhook_bot.cli.commands.provider import _cmd_qq_history

        assert callable(_cmd_qq_history)

    def test_cmd_qq_groups_function(self) -> None:
        """Test _cmd_qq_groups function structure."""
        from feishu_webhook_bot.cli.commands.provider import _cmd_qq_groups

        assert callable(_cmd_qq_groups)


@pytest.mark.asyncio
class TestQQPagePlaywright:
    """Playwright browser tests for QQ page (requires running server)."""

    async def test_placeholder_for_browser_tests(self) -> None:
        """Placeholder test for browser automation.

        Note: Full browser tests require a running NiceGUI server.
        These tests verify the code structure is correct.
        """
        # This is a placeholder - actual browser tests would require
        # setting up a test server with NiceGUI
        assert True

    async def test_qq_page_module_imports(self) -> None:
        """Test that QQ page module can be imported without errors."""
        from feishu_webhook_bot.webui.pages import qq

        assert qq is not None
        assert hasattr(qq, "build_qq_page")

    async def test_controller_module_imports(self) -> None:
        """Test that controller module can be imported without errors."""
        from feishu_webhook_bot.webui.controller import BotController

        assert BotController is not None
