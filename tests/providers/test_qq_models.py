"""Tests for providers.qq.models module.

Tests cover:
- OnlineStatus enum
- QQUserInfo dataclass
- QQGroupInfo dataclass
- QQGroupMember dataclass
- QQMessage dataclass
- OneBotResponse model
"""

from __future__ import annotations

from feishu_webhook_bot.providers.qq.models import (
    OneBotResponse,
    OnlineStatus,
    QQGroupInfo,
    QQGroupMember,
    QQMessage,
    QQUserInfo,
)


class TestOnlineStatus:
    """Tests for OnlineStatus enum."""

    def test_online_status_values(self) -> None:
        """Test OnlineStatus enum values."""
        assert OnlineStatus.ONLINE.value == 11
        assert OnlineStatus.AWAY.value == 31
        assert OnlineStatus.INVISIBLE.value == 41
        assert OnlineStatus.BUSY.value == 50
        assert OnlineStatus.Q_ME.value == 60
        assert OnlineStatus.DO_NOT_DISTURB.value == 70

    def test_online_status_from_value(self) -> None:
        """Test creating OnlineStatus from value."""
        assert OnlineStatus(11) == OnlineStatus.ONLINE
        assert OnlineStatus(31) == OnlineStatus.AWAY

    def test_online_status_is_int(self) -> None:
        """Test OnlineStatus can be used as int."""
        status = OnlineStatus.ONLINE

        assert isinstance(status.value, int)
        assert status == 11


class TestQQUserInfo:
    """Tests for QQUserInfo dataclass."""

    def test_create_user_info(self) -> None:
        """Test creating QQUserInfo."""
        user = QQUserInfo(
            user_id=123456789,
            nickname="TestUser",
            sex="male",
            age=25,
            remark="Friend",
        )

        assert user.user_id == 123456789
        assert user.nickname == "TestUser"
        assert user.sex == "male"
        assert user.age == 25
        assert user.remark == "Friend"

    def test_user_info_defaults(self) -> None:
        """Test QQUserInfo default values."""
        user = QQUserInfo(
            user_id=123456789,
            nickname="Test",
        )

        assert user.sex == "unknown"
        assert user.age == 0
        assert user.remark == ""

    def test_user_info_equality(self) -> None:
        """Test QQUserInfo equality."""
        user1 = QQUserInfo(user_id=123, nickname="Test")
        user2 = QQUserInfo(user_id=123, nickname="Test")

        assert user1 == user2


class TestQQGroupInfo:
    """Tests for QQGroupInfo dataclass."""

    def test_create_group_info(self) -> None:
        """Test creating QQGroupInfo."""
        group = QQGroupInfo(
            group_id=987654321,
            group_name="Test Group",
            member_count=100,
            max_member_count=500,
        )

        assert group.group_id == 987654321
        assert group.group_name == "Test Group"
        assert group.member_count == 100
        assert group.max_member_count == 500

    def test_group_info_defaults(self) -> None:
        """Test QQGroupInfo default values."""
        group = QQGroupInfo(
            group_id=123456,
            group_name="Group",
        )

        assert group.member_count == 0
        assert group.max_member_count == 0


class TestQQGroupMember:
    """Tests for QQGroupMember dataclass."""

    def test_create_group_member(self) -> None:
        """Test creating QQGroupMember."""
        member = QQGroupMember(
            group_id=987654321,
            user_id=123456789,
            nickname="Test",
            card="Admin",
            sex="female",
            age=30,
            role="admin",
            title="VIP",
            join_time=1704067200,
            last_sent_time=1704153600,
        )

        assert member.group_id == 987654321
        assert member.user_id == 123456789
        assert member.nickname == "Test"
        assert member.card == "Admin"
        assert member.sex == "female"
        assert member.age == 30
        assert member.role == "admin"
        assert member.title == "VIP"
        assert member.join_time == 1704067200
        assert member.last_sent_time == 1704153600

    def test_group_member_defaults(self) -> None:
        """Test QQGroupMember default values."""
        member = QQGroupMember(
            group_id=123,
            user_id=456,
            nickname="Test",
        )

        assert member.card == ""
        assert member.sex == "unknown"
        assert member.age == 0
        assert member.role == "member"
        assert member.title == ""
        assert member.join_time == 0
        assert member.last_sent_time == 0

    def test_group_member_roles(self) -> None:
        """Test different group member roles."""
        owner = QQGroupMember(
            group_id=123,
            user_id=1,
            nickname="Owner",
            role="owner",
        )
        admin = QQGroupMember(
            group_id=123,
            user_id=2,
            nickname="Admin",
            role="admin",
        )
        member = QQGroupMember(
            group_id=123,
            user_id=3,
            nickname="Member",
            role="member",
        )

        assert owner.role == "owner"
        assert admin.role == "admin"
        assert member.role == "member"


class TestQQMessage:
    """Tests for QQMessage dataclass."""

    def test_create_private_message(self) -> None:
        """Test creating private message."""
        msg = QQMessage(
            message_id=12345,
            message_type="private",
            sender_id=123456789,
            sender_nickname="Alice",
            content=[{"type": "text", "data": {"text": "Hello"}}],
            time=1704067200,
        )

        assert msg.message_id == 12345
        assert msg.message_type == "private"
        assert msg.sender_id == 123456789
        assert msg.sender_nickname == "Alice"
        assert len(msg.content) == 1
        assert msg.time == 1704067200
        assert msg.group_id is None

    def test_create_group_message(self) -> None:
        """Test creating group message."""
        msg = QQMessage(
            message_id=67890,
            message_type="group",
            sender_id=123456789,
            sender_nickname="Bob",
            content=[{"type": "text", "data": {"text": "Hi everyone"}}],
            time=1704067200,
            group_id=987654321,
        )

        assert msg.message_type == "group"
        assert msg.group_id == 987654321

    def test_message_with_complex_content(self) -> None:
        """Test message with multiple content segments."""
        msg = QQMessage(
            message_id=11111,
            message_type="group",
            sender_id=123,
            sender_nickname="Test",
            content=[
                {"type": "text", "data": {"text": "Hello "}},
                {"type": "at", "data": {"qq": "456"}},
                {"type": "text", "data": {"text": " world"}},
                {"type": "image", "data": {"file": "abc.jpg", "url": "https://..."}},
            ],
            time=1704067200,
            group_id=999,
        )

        assert len(msg.content) == 4
        assert msg.content[0]["type"] == "text"
        assert msg.content[1]["type"] == "at"
        assert msg.content[3]["type"] == "image"


class TestOneBotResponse:
    """Tests for OneBotResponse model."""

    def test_success_response(self) -> None:
        """Test successful response."""
        response = OneBotResponse(
            status="ok",
            retcode=0,
            data={"message_id": 12345},
        )

        assert response.status == "ok"
        assert response.retcode == 0
        assert response.data == {"message_id": 12345}
        assert response.msg == ""
        assert response.wording == ""

    def test_failed_response(self) -> None:
        """Test failed response."""
        response = OneBotResponse(
            status="failed",
            retcode=100,
            msg="INVALID_OPERATION",
            wording="Operation not allowed",
        )

        assert response.status == "failed"
        assert response.retcode == 100
        assert response.msg == "INVALID_OPERATION"
        assert response.wording == "Operation not allowed"
        assert response.data is None

    def test_async_response(self) -> None:
        """Test async response."""
        response = OneBotResponse(
            status="async",
            retcode=1,
        )

        assert response.status == "async"
        assert response.retcode == 1

    def test_response_defaults(self) -> None:
        """Test response default values."""
        response = OneBotResponse(status="ok")

        assert response.retcode == 0
        assert response.data is None
        assert response.msg == ""
        assert response.wording == ""

    def test_response_with_list_data(self) -> None:
        """Test response with list data."""
        response = OneBotResponse(
            status="ok",
            retcode=0,
            data=[
                {"user_id": 123, "nickname": "User1"},
                {"user_id": 456, "nickname": "User2"},
            ],
        )

        assert isinstance(response.data, list)
        assert len(response.data) == 2
