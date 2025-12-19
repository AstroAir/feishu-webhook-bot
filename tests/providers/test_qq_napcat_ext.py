"""Tests for providers.qq.napcat extension modules.

Tests cover:
- NapcatPokeMixin
- NapcatAIVoiceMixin
- NapcatMessageExtMixin
- NapcatGroupExtMixin
- NapcatFileMixin
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.providers.qq.models import OnlineStatus
from feishu_webhook_bot.providers.qq.napcat.ai_voice import NapcatAIVoiceMixin
from feishu_webhook_bot.providers.qq.napcat.file import NapcatFileMixin
from feishu_webhook_bot.providers.qq.napcat.group_ext import NapcatGroupExtMixin
from feishu_webhook_bot.providers.qq.napcat.message_ext import NapcatMessageExtMixin
from feishu_webhook_bot.providers.qq.napcat.poke import NapcatPokeMixin


class MockConfig:
    """Mock config for testing."""

    def __init__(self, enable_ai_voice: bool = True):
        self.enable_ai_voice = enable_ai_voice


class MockNapcatProvider(
    NapcatPokeMixin,
    NapcatAIVoiceMixin,
    NapcatMessageExtMixin,
    NapcatGroupExtMixin,
    NapcatFileMixin,
):
    """Mock provider for testing NapCat mixins."""

    def __init__(self, enable_ai_voice: bool = True):
        self.config = MockConfig(enable_ai_voice)
        self._api_response = None
        self._api_error = None

    def _call_api(self, endpoint: str, payload: dict) -> any:
        if self._api_error:
            raise self._api_error
        return self._api_response

    def _parse_target(self, target: str) -> tuple[int | None, int | None]:
        parts = target.split(":")
        if len(parts) != 2:
            return None, None
        target_type, target_id = parts[0], parts[1]
        try:
            if target_type == "private":
                return int(target_id), None
            elif target_type == "group":
                return None, int(target_id)
        except ValueError:
            pass
        return None, None

    def set_response(self, response):
        self._api_response = response
        self._api_error = None

    def set_error(self, error):
        self._api_error = error
        self._api_response = None


# ==============================================================================
# NapcatPokeMixin Tests
# ==============================================================================


class TestNapcatPokeMixin:
    """Tests for NapcatPokeMixin."""

    @pytest.fixture
    def provider(self):
        return MockNapcatProvider()

    def test_send_poke_success(self, provider):
        """Test sending poke."""
        provider.set_response(None)

        result = provider.send_poke(123456789)

        assert result is True

    def test_send_poke_group(self, provider):
        """Test sending group poke."""
        provider.set_response(None)

        result = provider.send_poke(123456789, group_id=987654321)

        assert result is True

    def test_send_poke_failure(self, provider):
        """Test poke failure."""
        provider.set_error(Exception("Failed"))

        result = provider.send_poke(123456789)

        assert result is False

    def test_group_poke_success(self, provider):
        """Test group poke."""
        provider.set_response(None)

        result = provider.group_poke(987654321, 123456789)

        assert result is True

    def test_group_poke_failure(self, provider):
        """Test group poke failure."""
        provider.set_error(Exception("Error"))

        result = provider.group_poke(987654321, 123456789)

        assert result is False

    def test_friend_poke_success(self, provider):
        """Test friend poke."""
        provider.set_response(None)

        result = provider.friend_poke(123456789)

        assert result is True

    def test_friend_poke_failure(self, provider):
        """Test friend poke failure."""
        provider.set_error(Exception("Error"))

        result = provider.friend_poke(123456789)

        assert result is False


# ==============================================================================
# NapcatAIVoiceMixin Tests
# ==============================================================================


class TestNapcatAIVoiceMixin:
    """Tests for NapcatAIVoiceMixin."""

    @pytest.fixture
    def provider(self):
        return MockNapcatProvider(enable_ai_voice=True)

    @pytest.fixture
    def provider_disabled(self):
        return MockNapcatProvider(enable_ai_voice=False)

    def test_get_ai_characters_success(self, provider):
        """Test getting AI characters."""
        provider.set_response(
            [
                {"character_id": "1", "name": "Character 1"},
                {"character_id": "2", "name": "Character 2"},
            ]
        )

        result = provider.get_ai_characters(123456)

        assert len(result) == 2
        assert result[0]["character_id"] == "1"

    def test_get_ai_characters_disabled(self, provider_disabled):
        """Test AI characters when disabled."""
        result = provider_disabled.get_ai_characters(123456)

        assert result == []

    def test_get_ai_characters_failure(self, provider):
        """Test AI characters failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_ai_characters(123456)

        assert result == []

    def test_get_ai_record_success(self, provider):
        """Test getting AI record."""
        provider.set_response({"data": "https://example.com/voice.mp3"})

        result = provider.get_ai_record("char_1", 123456, "Hello world")

        assert result == "https://example.com/voice.mp3"

    def test_get_ai_record_disabled(self, provider_disabled):
        """Test AI record when disabled."""
        result = provider_disabled.get_ai_record("char_1", 123456, "Hello")

        assert result == ""

    def test_get_ai_record_failure(self, provider):
        """Test AI record failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_ai_record("char_1", 123456, "Hello")

        assert result == ""

    def test_send_group_ai_record_success(self, provider):
        """Test sending group AI record."""
        provider.set_response({"message_id": 12345})

        result = provider.send_group_ai_record(123456, "char_1", "Hello")

        assert result.success is True
        assert result.message_id == "12345"

    def test_send_group_ai_record_disabled(self, provider_disabled):
        """Test sending AI record when disabled."""
        result = provider_disabled.send_group_ai_record(123456, "char_1", "Hello")

        assert result.success is False
        assert "not enabled" in result.error

    def test_send_group_ai_record_failure(self, provider):
        """Test sending AI record failure."""
        provider.set_error(Exception("API error"))

        result = provider.send_group_ai_record(123456, "char_1", "Hello")

        assert result.success is False


# ==============================================================================
# NapcatMessageExtMixin Tests
# ==============================================================================


class TestNapcatMessageExtMixin:
    """Tests for NapcatMessageExtMixin."""

    @pytest.fixture
    def provider(self):
        return MockNapcatProvider()

    def test_set_msg_emoji_like_success(self, provider):
        """Test setting emoji reaction."""
        provider.set_response(None)

        result = provider.set_msg_emoji_like(12345, "128077")

        assert result is True

    def test_set_msg_emoji_like_failure(self, provider):
        """Test emoji reaction failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_msg_emoji_like(12345, "128077")

        assert result is False

    def test_mark_msg_as_read_private(self, provider):
        """Test marking private message as read."""
        provider.set_response(None)

        result = provider.mark_msg_as_read("private:123456789")

        assert result is True

    def test_mark_msg_as_read_group(self, provider):
        """Test marking group messages as read."""
        provider.set_response(None)

        result = provider.mark_msg_as_read("group:987654321")

        assert result is True

    def test_mark_msg_as_read_invalid_target(self, provider):
        """Test marking with invalid target."""
        result = provider.mark_msg_as_read("invalid")

        assert result is False

    def test_mark_msg_as_read_failure(self, provider):
        """Test mark as read failure."""
        provider.set_error(Exception("Error"))

        result = provider.mark_msg_as_read("private:123")

        assert result is False

    def test_get_group_msg_history_success(self, provider):
        """Test getting group message history."""
        provider.set_response(
            {
                "messages": [
                    {"message_id": 1, "content": "Hello"},
                    {"message_id": 2, "content": "World"},
                ]
            }
        )

        result = provider.get_group_msg_history(123456, message_seq=0, count=20)

        assert len(result) == 2

    def test_get_group_msg_history_failure(self, provider):
        """Test history retrieval failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_group_msg_history(123456)

        assert result == []

    def test_get_friend_msg_history_success(self, provider):
        """Test getting friend message history."""
        provider.set_response(
            {
                "messages": [
                    {"message_id": 1, "content": "Hi"},
                ]
            }
        )

        result = provider.get_friend_msg_history(123456)

        assert len(result) == 1

    def test_get_friend_msg_history_failure(self, provider):
        """Test friend history failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_friend_msg_history(123456)

        assert result == []

    def test_get_essence_msg_list_success(self, provider):
        """Test getting essence messages."""
        provider.set_response(
            [
                {"message_id": 1, "sender_id": 111},
                {"message_id": 2, "sender_id": 222},
            ]
        )

        result = provider.get_essence_msg_list(123456)

        assert len(result) == 2

    def test_get_essence_msg_list_failure(self, provider):
        """Test essence messages failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_essence_msg_list(123456)

        assert result == []

    def test_set_essence_msg_success(self, provider):
        """Test setting essence message."""
        provider.set_response(None)

        result = provider.set_essence_msg(12345)

        assert result is True

    def test_set_essence_msg_failure(self, provider):
        """Test set essence failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_essence_msg(12345)

        assert result is False

    def test_delete_essence_msg_success(self, provider):
        """Test deleting essence message."""
        provider.set_response(None)

        result = provider.delete_essence_msg(12345)

        assert result is True

    def test_delete_essence_msg_failure(self, provider):
        """Test delete essence failure."""
        provider.set_error(Exception("Error"))

        result = provider.delete_essence_msg(12345)

        assert result is False

    def test_forward_friend_single_msg_success(self, provider):
        """Test forwarding to friend."""
        provider.set_response({"message_id": 67890})

        result = provider.forward_friend_single_msg(12345, 111222333)

        assert result.success is True
        assert result.message_id == "67890"

    def test_forward_friend_single_msg_failure(self, provider):
        """Test forward to friend failure."""
        provider.set_error(Exception("Error"))

        result = provider.forward_friend_single_msg(12345, 111222333)

        assert result.success is False

    def test_forward_group_single_msg_success(self, provider):
        """Test forwarding to group."""
        provider.set_response({"message_id": 67890})

        result = provider.forward_group_single_msg(12345, 987654321)

        assert result.success is True

    def test_forward_group_single_msg_failure(self, provider):
        """Test forward to group failure."""
        provider.set_error(Exception("Error"))

        result = provider.forward_group_single_msg(12345, 987654321)

        assert result.success is False

    def test_ocr_image_success(self, provider):
        """Test OCR image."""
        provider.set_response(
            {
                "texts": [
                    {"text": "Hello", "x": 0, "y": 0},
                    {"text": "World", "x": 100, "y": 0},
                ]
            }
        )

        result = provider.ocr_image("https://example.com/image.jpg")

        assert len(result) == 2
        assert result[0]["text"] == "Hello"

    def test_ocr_image_failure(self, provider):
        """Test OCR failure."""
        provider.set_error(Exception("Error"))

        result = provider.ocr_image("https://example.com/image.jpg")

        assert result == []

    def test_fetch_custom_face_success(self, provider):
        """Test fetching custom faces."""
        provider.set_response(
            [
                {"face_id": "1", "url": "https://..."},
                {"face_id": "2", "url": "https://..."},
            ]
        )

        result = provider.fetch_custom_face(count=10)

        assert len(result) == 2

    def test_fetch_custom_face_failure(self, provider):
        """Test fetch faces failure."""
        provider.set_error(Exception("Error"))

        result = provider.fetch_custom_face()

        assert result == []

    def test_fetch_emoji_like_success(self, provider):
        """Test fetching emoji reactions."""
        provider.set_response(
            [
                {"user_id": 111, "nickname": "User1"},
                {"user_id": 222, "nickname": "User2"},
            ]
        )

        result = provider.fetch_emoji_like(12345, "128077")

        assert len(result) == 2

    def test_fetch_emoji_like_failure(self, provider):
        """Test fetch emoji like failure."""
        provider.set_error(Exception("Error"))

        result = provider.fetch_emoji_like(12345, "128077")

        assert result == []

    def test_translate_en2zh_success(self, provider):
        """Test English to Chinese translation."""
        provider.set_response(["你好", "世界"])

        result = provider.translate_en2zh(["hello", "world"])

        assert len(result) == 2
        assert result[0] == "你好"

    def test_translate_en2zh_failure(self, provider):
        """Test translation failure."""
        provider.set_error(Exception("Error"))

        result = provider.translate_en2zh(["hello"])

        assert result == []


# ==============================================================================
# NapcatGroupExtMixin Tests
# ==============================================================================


class TestNapcatGroupExtMixin:
    """Tests for NapcatGroupExtMixin."""

    @pytest.fixture
    def provider(self):
        return MockNapcatProvider()

    def test_get_group_notice_success(self, provider):
        """Test getting group notices."""
        provider.set_response(
            [
                {"sender_id": 111, "publish_time": 1704067200, "content": "Notice 1"},
            ]
        )

        result = provider.get_group_notice(123456)

        assert len(result) == 1

    def test_get_group_notice_failure(self, provider):
        """Test get notices failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_group_notice(123456)

        assert result == []

    def test_send_group_notice_success(self, provider):
        """Test sending group notice."""
        provider.set_response(None)

        result = provider.send_group_notice(123456, "Important announcement")

        assert result is True

    def test_send_group_notice_with_image(self, provider):
        """Test sending notice with image."""
        provider.set_response(None)

        result = provider.send_group_notice(123456, "Notice", image="https://...")

        assert result is True

    def test_send_group_notice_failure(self, provider):
        """Test send notice failure."""
        provider.set_error(Exception("Error"))

        result = provider.send_group_notice(123456, "Notice")

        assert result is False

    def test_del_group_notice_success(self, provider):
        """Test deleting group notice."""
        provider.set_response(None)

        result = provider.del_group_notice(123456, "notice_id_123")

        assert result is True

    def test_del_group_notice_failure(self, provider):
        """Test delete notice failure."""
        provider.set_error(Exception("Error"))

        result = provider.del_group_notice(123456, "notice_id_123")

        assert result is False

    def test_set_group_sign_success(self, provider):
        """Test group sign-in."""
        provider.set_response(None)

        result = provider.set_group_sign(123456)

        assert result is True

    def test_set_group_sign_failure(self, provider):
        """Test sign-in failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_group_sign(123456)

        assert result is False

    def test_set_online_status_success(self, provider):
        """Test setting online status."""
        provider.set_response(None)

        result = provider.set_online_status(OnlineStatus.ONLINE)

        assert result is True

    def test_set_online_status_int(self, provider):
        """Test setting status with int."""
        provider.set_response(None)

        result = provider.set_online_status(11)

        assert result is True

    def test_set_online_status_failure(self, provider):
        """Test set status failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_online_status(OnlineStatus.BUSY)

        assert result is False

    def test_set_qq_avatar_success(self, provider):
        """Test setting QQ avatar."""
        provider.set_response(None)

        result = provider.set_qq_avatar("https://example.com/avatar.jpg")

        assert result is True

    def test_set_qq_avatar_failure(self, provider):
        """Test set avatar failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_qq_avatar("https://example.com/avatar.jpg")

        assert result is False

    def test_get_profile_like_success(self, provider):
        """Test getting profile likes."""
        provider.set_response({"total_count": 100, "today_count": 5})

        result = provider.get_profile_like()

        assert result["total_count"] == 100

    def test_get_profile_like_failure(self, provider):
        """Test profile like failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_profile_like()

        assert result == {}

    def test_set_input_status_success(self, provider):
        """Test setting input status."""
        provider.set_response(None)

        result = provider.set_input_status(123456789, event_type=1)

        assert result is True

    def test_set_input_status_failure(self, provider):
        """Test input status failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_input_status(123456789)

        assert result is False

    def test_get_cookies_success(self, provider):
        """Test getting cookies."""
        provider.set_response({"cookies": "session=abc123"})

        result = provider.get_cookies("qq.com")

        assert result == "session=abc123"

    def test_get_cookies_failure(self, provider):
        """Test get cookies failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_cookies()

        assert result == ""

    def test_get_clientkey_success(self, provider):
        """Test getting client key."""
        provider.set_response({"clientkey": "key123"})

        result = provider.get_clientkey()

        assert result == "key123"

    def test_get_clientkey_failure(self, provider):
        """Test get clientkey failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_clientkey()

        assert result == ""

    def test_get_group_info_ex_success(self, provider):
        """Test getting extended group info."""
        provider.set_response(
            {
                "group_id": 123456,
                "group_name": "Test",
                "owner_id": 111,
            }
        )

        result = provider.get_group_info_ex(123456)

        assert result["group_name"] == "Test"

    def test_get_group_info_ex_failure(self, provider):
        """Test extended info failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_group_info_ex(123456)

        assert result == {}

    def test_set_group_portrait_success(self, provider):
        """Test setting group portrait."""
        provider.set_response(None)

        result = provider.set_group_portrait(123456, "https://example.com/avatar.jpg")

        assert result is True

    def test_set_group_portrait_failure(self, provider):
        """Test set portrait failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_group_portrait(123456, "https://...")

        assert result is False

    def test_get_group_honor_info_success(self, provider):
        """Test getting group honor info."""
        provider.set_response(
            {
                "group_id": 123456,
                "current_talkative": {"user_id": 111},
            }
        )

        result = provider.get_group_honor_info(123456)

        assert "current_talkative" in result

    def test_get_group_honor_info_type(self, provider):
        """Test honor info with specific type."""
        provider.set_response({"talkative_list": []})

        result = provider.get_group_honor_info(123456, honor_type="talkative")

        assert result is not None

    def test_get_group_honor_info_failure(self, provider):
        """Test honor info failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_group_honor_info(123456)

        assert result == {}

    def test_get_group_at_all_remain_success(self, provider):
        """Test getting @all remain count."""
        provider.set_response(
            {
                "can_at_all": True,
                "remain_at_all_count_for_group": 5,
                "remain_at_all_count_for_uin": 2,
            }
        )

        result = provider.get_group_at_all_remain(123456)

        assert result["can_at_all"] is True
        assert result["remain_at_all_count_for_group"] == 5

    def test_get_group_at_all_remain_failure(self, provider):
        """Test @all remain failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_group_at_all_remain(123456)

        assert result == {}


# ==============================================================================
# NapcatFileMixin Tests
# ==============================================================================


class TestNapcatFileMixin:
    """Tests for NapcatFileMixin."""

    @pytest.fixture
    def provider(self):
        return MockNapcatProvider()

    def test_get_file_success(self, provider):
        """Test getting file info."""
        provider.set_response(
            {
                "file": "/path/to/file.txt",
                "url": "https://example.com/file.txt",
                "file_size": 1024,
                "file_name": "file.txt",
            }
        )

        result = provider.get_file("file_id_123")

        assert result["file_name"] == "file.txt"
        assert result["file_size"] == 1024

    def test_get_file_failure(self, provider):
        """Test get file failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_file("file_id_123")

        assert result == {}

    def test_get_private_file_url_success(self, provider):
        """Test getting private file URL."""
        provider.set_response({"url": "https://example.com/download/file.txt"})

        result = provider.get_private_file_url("file_id_123")

        assert result == "https://example.com/download/file.txt"

    def test_get_private_file_url_failure(self, provider):
        """Test private file URL failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_private_file_url("file_id_123")

        assert result == ""

    def test_move_group_file_success(self, provider):
        """Test moving group file."""
        provider.set_response(None)

        result = provider.move_group_file(123456, "file_id", "dir_id")

        assert result is True

    def test_move_group_file_failure(self, provider):
        """Test move file failure."""
        provider.set_error(Exception("Error"))

        result = provider.move_group_file(123456, "file_id", "dir_id")

        assert result is False

    def test_rename_group_file_success(self, provider):
        """Test renaming group file."""
        provider.set_response(None)

        result = provider.rename_group_file(123456, "file_id", "new_name.txt")

        assert result is True

    def test_rename_group_file_failure(self, provider):
        """Test rename file failure."""
        provider.set_error(Exception("Error"))

        result = provider.rename_group_file(123456, "file_id", "new_name.txt")

        assert result is False

    def test_trans_group_file_success(self, provider):
        """Test transferring group file."""
        provider.set_response({"file_id": "new_file_id_123"})

        result = provider.trans_group_file(123456, "file_id")

        assert result == "new_file_id_123"

    def test_trans_group_file_failure(self, provider):
        """Test transfer file failure."""
        provider.set_error(Exception("Error"))

        result = provider.trans_group_file(123456, "file_id")

        assert result == ""
