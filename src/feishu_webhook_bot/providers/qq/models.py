"""Data models for QQ/Napcat providers.

This module contains all data models used by QQ providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel


class OnlineStatus(int, Enum):
    """QQ online status codes."""

    ONLINE = 11  # 在线
    AWAY = 31  # 离开
    INVISIBLE = 41  # 隐身
    BUSY = 50  # 忙碌
    Q_ME = 60  # Q我吧
    DO_NOT_DISTURB = 70  # 请勿打扰


@dataclass
class QQUserInfo:
    """QQ user information.

    Attributes:
        user_id: QQ number.
        nickname: User's nickname.
        sex: Gender (male, female, unknown).
        age: User's age.
        remark: Friend remark name.
    """

    user_id: int
    nickname: str
    sex: str = "unknown"
    age: int = 0
    remark: str = ""


@dataclass
class QQGroupInfo:
    """QQ group information.

    Attributes:
        group_id: Group number.
        group_name: Group name.
        member_count: Current member count.
        max_member_count: Maximum member capacity.
    """

    group_id: int
    group_name: str
    member_count: int = 0
    max_member_count: int = 0


@dataclass
class QQGroupMember:
    """QQ group member information.

    Attributes:
        group_id: Group number.
        user_id: Member's QQ number.
        nickname: Member's QQ nickname.
        card: Group card/nickname.
        sex: Gender.
        age: Age.
        role: Role (owner, admin, member).
        title: Special title.
        join_time: Join timestamp.
        last_sent_time: Last message timestamp.
    """

    group_id: int
    user_id: int
    nickname: str
    card: str = ""
    sex: str = "unknown"
    age: int = 0
    role: str = "member"
    title: str = ""
    join_time: int = 0
    last_sent_time: int = 0


@dataclass
class QQMessage:
    """QQ message information.

    Attributes:
        message_id: Message ID.
        message_type: Message type (private, group).
        sender_id: Sender's QQ number.
        sender_nickname: Sender's nickname.
        content: Message content segments.
        time: Message timestamp.
        group_id: Group ID (for group messages).
    """

    message_id: int
    message_type: str
    sender_id: int
    sender_nickname: str
    content: list[dict[str, Any]]
    time: int
    group_id: int | None = None


class OneBotResponse(BaseModel):
    """OneBot API response model.

    Attributes:
        status: Response status (ok, failed, async).
        retcode: Return code.
        data: Response data.
        msg: Error message.
        wording: Error wording.
    """

    status: str  # ok, failed, async
    retcode: int = 0
    data: Any = None
    msg: str = ""
    wording: str = ""
