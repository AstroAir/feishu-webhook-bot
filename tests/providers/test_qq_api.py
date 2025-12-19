"""Tests for providers.qq.api module.

Tests cover:
- OneBotGroupInfoMixin
- OneBotGroupAdminMixin
- OneBotMessageMixin
- OneBotUserMixin
- OneBotRequestMixin
- OneBotSystemMixin
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.providers.qq.api.group import OneBotGroupInfoMixin
from feishu_webhook_bot.providers.qq.api.group_admin import OneBotGroupAdminMixin
from feishu_webhook_bot.providers.qq.api.message import OneBotMessageMixin
from feishu_webhook_bot.providers.qq.api.request import OneBotRequestMixin
from feishu_webhook_bot.providers.qq.api.system import OneBotSystemMixin
from feishu_webhook_bot.providers.qq.api.user import OneBotUserMixin
from feishu_webhook_bot.providers.qq.models import QQGroupInfo, QQGroupMember, QQUserInfo


class MockApiProvider(
    OneBotGroupInfoMixin,
    OneBotGroupAdminMixin,
    OneBotMessageMixin,
    OneBotUserMixin,
    OneBotRequestMixin,
    OneBotSystemMixin,
):
    """Mock provider for testing API mixins."""

    def __init__(self):
        self._api_response = None
        self._api_error = None
        self._login_info = None  # Required by OneBotUserMixin

    def _call_api(self, endpoint: str, payload: dict) -> any:
        if self._api_error:
            raise self._api_error
        return self._api_response

    def set_response(self, response):
        self._api_response = response
        self._api_error = None

    def set_error(self, error):
        self._api_error = error
        self._api_response = None


# ==============================================================================
# OneBotGroupInfoMixin Tests
# ==============================================================================


class TestOneBotGroupInfoMixin:
    """Tests for OneBotGroupInfoMixin."""

    @pytest.fixture
    def provider(self):
        return MockApiProvider()

    def test_get_group_info_success(self, provider):
        """Test getting group info."""
        provider.set_response(
            {
                "group_id": 123456789,
                "group_name": "Test Group",
                "member_count": 100,
                "max_member_count": 500,
            }
        )

        result = provider.get_group_info(123456789)

        assert result is not None
        assert isinstance(result, QQGroupInfo)
        assert result.group_id == 123456789
        assert result.group_name == "Test Group"
        assert result.member_count == 100
        assert result.max_member_count == 500

    def test_get_group_info_failure(self, provider):
        """Test getting group info failure."""
        provider.set_error(Exception("API error"))

        result = provider.get_group_info(123456789)

        assert result is None

    def test_get_group_info_no_cache(self, provider):
        """Test getting group info without cache."""
        provider.set_response(
            {
                "group_id": 123,
                "group_name": "Group",
            }
        )

        result = provider.get_group_info(123, no_cache=True)

        assert result is not None

    def test_get_group_list_success(self, provider):
        """Test getting group list."""
        provider.set_response(
            [
                {"group_id": 111, "group_name": "Group 1", "member_count": 10},
                {"group_id": 222, "group_name": "Group 2", "member_count": 20},
            ]
        )

        result = provider.get_group_list()

        assert len(result) == 2
        assert all(isinstance(g, QQGroupInfo) for g in result)
        assert result[0].group_id == 111
        assert result[1].group_name == "Group 2"

    def test_get_group_list_empty(self, provider):
        """Test getting empty group list."""
        provider.set_response([])

        result = provider.get_group_list()

        assert result == []

    def test_get_group_list_failure(self, provider):
        """Test getting group list failure."""
        provider.set_error(Exception("API error"))

        result = provider.get_group_list()

        assert result == []

    def test_get_group_member_info_success(self, provider):
        """Test getting group member info."""
        provider.set_response(
            {
                "group_id": 123,
                "user_id": 456,
                "nickname": "TestUser",
                "card": "Admin",
                "role": "admin",
                "title": "VIP",
            }
        )

        result = provider.get_group_member_info(123, 456)

        assert result is not None
        assert isinstance(result, QQGroupMember)
        assert result.user_id == 456
        assert result.nickname == "TestUser"
        assert result.card == "Admin"
        assert result.role == "admin"

    def test_get_group_member_info_failure(self, provider):
        """Test getting group member info failure."""
        provider.set_error(Exception("Not found"))

        result = provider.get_group_member_info(123, 456)

        assert result is None

    def test_get_group_member_list_success(self, provider):
        """Test getting group member list."""
        provider.set_response(
            [
                {"user_id": 111, "nickname": "User1", "role": "owner"},
                {"user_id": 222, "nickname": "User2", "role": "admin"},
                {"user_id": 333, "nickname": "User3", "role": "member"},
            ]
        )

        result = provider.get_group_member_list(123)

        assert len(result) == 3
        assert all(isinstance(m, QQGroupMember) for m in result)
        assert result[0].role == "owner"

    def test_get_group_member_list_failure(self, provider):
        """Test getting group member list failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_group_member_list(123)

        assert result == []


# ==============================================================================
# OneBotGroupAdminMixin Tests
# ==============================================================================


class TestOneBotGroupAdminMixin:
    """Tests for OneBotGroupAdminMixin."""

    @pytest.fixture
    def provider(self):
        return MockApiProvider()

    def test_set_group_kick_success(self, provider):
        """Test kicking group member."""
        provider.set_response(None)

        result = provider.set_group_kick(123, 456)

        assert result is True

    def test_set_group_kick_reject_add(self, provider):
        """Test kicking and rejecting future requests."""
        provider.set_response(None)

        result = provider.set_group_kick(123, 456, reject_add_request=True)

        assert result is True

    def test_set_group_kick_failure(self, provider):
        """Test kick failure."""
        provider.set_error(Exception("Permission denied"))

        result = provider.set_group_kick(123, 456)

        assert result is False

    def test_set_group_ban_success(self, provider):
        """Test banning group member."""
        provider.set_response(None)

        result = provider.set_group_ban(123, 456, duration=3600)

        assert result is True

    def test_set_group_ban_unban(self, provider):
        """Test unbanning member (duration=0)."""
        provider.set_response(None)

        result = provider.set_group_ban(123, 456, duration=0)

        assert result is True

    def test_set_group_ban_failure(self, provider):
        """Test ban failure."""
        provider.set_error(Exception("Not admin"))

        result = provider.set_group_ban(123, 456)

        assert result is False

    def test_set_group_whole_ban_success(self, provider):
        """Test whole group mute."""
        provider.set_response(None)

        result = provider.set_group_whole_ban(123, enable=True)

        assert result is True

    def test_set_group_whole_ban_disable(self, provider):
        """Test disabling whole group mute."""
        provider.set_response(None)

        result = provider.set_group_whole_ban(123, enable=False)

        assert result is True

    def test_set_group_whole_ban_failure(self, provider):
        """Test whole ban failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_group_whole_ban(123)

        assert result is False

    def test_set_group_admin_success(self, provider):
        """Test setting group admin."""
        provider.set_response(None)

        result = provider.set_group_admin(123, 456, enable=True)

        assert result is True

    def test_set_group_admin_remove(self, provider):
        """Test removing group admin."""
        provider.set_response(None)

        result = provider.set_group_admin(123, 456, enable=False)

        assert result is True

    def test_set_group_admin_failure(self, provider):
        """Test set admin failure."""
        provider.set_error(Exception("Not owner"))

        result = provider.set_group_admin(123, 456)

        assert result is False

    def test_set_group_card_success(self, provider):
        """Test setting member card."""
        provider.set_response(None)

        result = provider.set_group_card(123, 456, "New Card")

        assert result is True

    def test_set_group_card_clear(self, provider):
        """Test clearing member card."""
        provider.set_response(None)

        result = provider.set_group_card(123, 456, "")

        assert result is True

    def test_set_group_card_failure(self, provider):
        """Test set card failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_group_card(123, 456, "Card")

        assert result is False

    def test_set_group_name_success(self, provider):
        """Test setting group name."""
        provider.set_response(None)

        result = provider.set_group_name(123, "New Name")

        assert result is True

    def test_set_group_name_failure(self, provider):
        """Test set name failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_group_name(123, "Name")

        assert result is False

    def test_set_group_leave_success(self, provider):
        """Test leaving group."""
        provider.set_response(None)

        result = provider.set_group_leave(123)

        assert result is True

    def test_set_group_leave_dismiss(self, provider):
        """Test dismissing group."""
        provider.set_response(None)

        result = provider.set_group_leave(123, is_dismiss=True)

        assert result is True

    def test_set_group_leave_failure(self, provider):
        """Test leave failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_group_leave(123)

        assert result is False

    def test_set_group_special_title_success(self, provider):
        """Test setting special title."""
        provider.set_response(None)

        result = provider.set_group_special_title(123, 456, "Special")

        assert result is True

    def test_set_group_special_title_with_duration(self, provider):
        """Test setting special title with duration."""
        provider.set_response(None)

        result = provider.set_group_special_title(123, 456, "Title", duration=86400)

        assert result is True

    def test_set_group_special_title_failure(self, provider):
        """Test set title failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_group_special_title(123, 456, "Title")

        assert result is False


# ==============================================================================
# OneBotMessageMixin Tests
# ==============================================================================


class TestOneBotMessageMixin:
    """Tests for OneBotMessageMixin."""

    @pytest.fixture
    def provider(self):
        return MockApiProvider()

    def test_delete_msg_success(self, provider):
        """Test deleting message."""
        provider.set_response(None)

        result = provider.delete_msg(12345)

        assert result is True

    def test_delete_msg_failure(self, provider):
        """Test delete message failure."""
        provider.set_error(Exception("Message not found"))

        result = provider.delete_msg(12345)

        assert result is False

    def test_get_msg_success(self, provider):
        """Test getting message."""
        provider.set_response(
            {
                "message_id": 12345,
                "message_type": "group",
                "sender": {"user_id": 111, "nickname": "Test"},
                "message": [{"type": "text", "data": {"text": "Hello"}}],
                "time": 1704067200,
                "group_id": 987654321,
            }
        )

        result = provider.get_msg(12345)

        assert result is not None
        assert result.message_id == 12345
        assert result.sender_id == 111

    def test_get_msg_failure(self, provider):
        """Test get message failure."""
        provider.set_error(Exception("Not found"))

        result = provider.get_msg(12345)

        assert result is None


# ==============================================================================
# OneBotUserMixin Tests
# ==============================================================================


class TestOneBotUserMixin:
    """Tests for OneBotUserMixin."""

    @pytest.fixture
    def provider(self):
        return MockApiProvider()

    def test_get_login_info_success(self, provider):
        """Test getting login info."""
        provider._login_info = None  # Reset cached info
        provider.set_response(
            {
                "user_id": 123456789,
                "nickname": "BotName",
            }
        )

        result = provider.get_login_info()

        assert result["user_id"] == 123456789
        assert result["nickname"] == "BotName"

    def test_get_login_info_cached(self, provider):
        """Test login info uses cache."""
        provider._login_info = {"user_id": 111, "nickname": "Cached"}
        provider.set_response({"user_id": 222, "nickname": "Fresh"})

        result = provider.get_login_info()

        assert result["user_id"] == 111  # Should return cached

    def test_get_login_info_failure(self, provider):
        """Test get login info failure."""
        provider._login_info = None
        provider.set_error(Exception("Error"))

        result = provider.get_login_info()

        assert result == {}

    def test_get_stranger_info_success(self, provider):
        """Test getting stranger info."""
        provider.set_response(
            {
                "user_id": 123456789,
                "nickname": "User",
                "sex": "male",
                "age": 25,
            }
        )

        result = provider.get_stranger_info(123456789)

        assert result is not None
        assert isinstance(result, QQUserInfo)
        assert result.nickname == "User"
        assert result.sex == "male"

    def test_get_stranger_info_failure(self, provider):
        """Test get stranger info failure."""
        provider.set_error(Exception("Not found"))

        result = provider.get_stranger_info(123456789)

        assert result is None

    def test_get_friend_list_success(self, provider):
        """Test getting friend list."""
        provider.set_response(
            [
                {"user_id": 111, "nickname": "Friend1", "remark": "F1"},
                {"user_id": 222, "nickname": "Friend2", "remark": ""},
            ]
        )

        result = provider.get_friend_list()

        assert len(result) == 2
        assert all(isinstance(u, QQUserInfo) for u in result)
        assert result[0].remark == "F1"

    def test_get_friend_list_failure(self, provider):
        """Test get friend list failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_friend_list()

        assert result == []


# ==============================================================================
# OneBotRequestMixin Tests
# ==============================================================================


class TestOneBotRequestMixin:
    """Tests for OneBotRequestMixin."""

    @pytest.fixture
    def provider(self):
        return MockApiProvider()

    def test_set_friend_add_request_approve(self, provider):
        """Test approving friend request."""
        provider.set_response(None)

        result = provider.set_friend_add_request("flag_123", approve=True)

        assert result is True

    def test_set_friend_add_request_reject(self, provider):
        """Test rejecting friend request."""
        provider.set_response(None)

        result = provider.set_friend_add_request("flag_123", approve=False)

        assert result is True

    def test_set_friend_add_request_with_remark(self, provider):
        """Test approving with remark."""
        provider.set_response(None)

        result = provider.set_friend_add_request("flag_123", approve=True, remark="My Friend")

        assert result is True

    def test_set_friend_add_request_failure(self, provider):
        """Test friend request handling failure."""
        provider.set_error(Exception("Invalid flag"))

        result = provider.set_friend_add_request("flag_123", approve=True)

        assert result is False

    def test_set_group_add_request_approve(self, provider):
        """Test approving group request."""
        provider.set_response(None)

        result = provider.set_group_add_request("flag_123", sub_type="add", approve=True)

        assert result is True

    def test_set_group_add_request_reject_with_reason(self, provider):
        """Test rejecting group request with reason."""
        provider.set_response(None)

        result = provider.set_group_add_request(
            "flag_123", sub_type="invite", approve=False, reason="Not allowed"
        )

        assert result is True

    def test_set_group_add_request_failure(self, provider):
        """Test group request handling failure."""
        provider.set_error(Exception("Error"))

        result = provider.set_group_add_request("flag_123", sub_type="add", approve=True)

        assert result is False


# ==============================================================================
# OneBotSystemMixin Tests
# ==============================================================================


class TestOneBotSystemMixin:
    """Tests for OneBotSystemMixin."""

    @pytest.fixture
    def provider(self):
        return MockApiProvider()

    def test_get_status_success(self, provider):
        """Test getting status."""
        provider.set_response(
            {
                "online": True,
                "good": True,
            }
        )

        result = provider.get_status()

        assert result["online"] is True
        assert result["good"] is True

    def test_get_status_failure(self, provider):
        """Test get status failure returns default."""
        provider.set_error(Exception("Error"))

        result = provider.get_status()

        assert result == {"online": False, "good": False}

    def test_get_version_info_success(self, provider):
        """Test getting version info."""
        provider.set_response(
            {
                "app_name": "Napcat",
                "app_version": "1.0.0",
                "protocol_version": "v11",
            }
        )

        result = provider.get_version_info()

        assert result["app_name"] == "Napcat"
        assert result["protocol_version"] == "v11"

    def test_get_version_info_failure(self, provider):
        """Test get version info failure."""
        provider.set_error(Exception("Error"))

        result = provider.get_version_info()

        assert result == {}

    def test_can_send_image_success(self, provider):
        """Test checking image sending capability."""
        provider.set_response({"yes": True})

        result = provider.can_send_image()

        assert result is True

    def test_can_send_image_no(self, provider):
        """Test image sending not available."""
        provider.set_response({"yes": False})

        result = provider.can_send_image()

        assert result is False

    def test_can_send_image_failure(self, provider):
        """Test can_send_image failure."""
        provider.set_error(Exception("Error"))

        result = provider.can_send_image()

        assert result is False

    def test_can_send_record_success(self, provider):
        """Test checking record sending capability."""
        provider.set_response({"yes": True})

        result = provider.can_send_record()

        assert result is True

    def test_can_send_record_failure(self, provider):
        """Test can_send_record failure."""
        provider.set_error(Exception("Error"))

        result = provider.can_send_record()

        assert result is False
