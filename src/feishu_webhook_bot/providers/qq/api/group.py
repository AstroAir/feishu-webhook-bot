"""OneBot11 group information API.

This module provides group-related API operations:
- Get group info
- Get group list
- Get group member info
- Get group member list
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger
from ..models import QQGroupInfo, QQGroupMember

logger = get_logger(__name__)


class OneBotGroupInfoMixin:
    """Mixin providing OneBot11 group information operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self.logger
    """

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def get_group_info(self, group_id: int, no_cache: bool = False) -> QQGroupInfo | None:
        """Get group information.

        Args:
            group_id: Group number.
            no_cache: Whether to bypass cache.

        Returns:
            QQGroupInfo object or None.
        """
        try:
            data = self._call_api(
                "/get_group_info",
                {"group_id": group_id, "no_cache": no_cache},
            )
            if data:
                return QQGroupInfo(
                    group_id=data.get("group_id", group_id),
                    group_name=data.get("group_name", ""),
                    member_count=data.get("member_count", 0),
                    max_member_count=data.get("max_member_count", 0),
                )
        except Exception as e:
            logger.error(f"Failed to get group info for {group_id}: {e}")
        return None

    def get_group_list(self) -> list[QQGroupInfo]:
        """Get bot's group list.

        Returns:
            List of QQGroupInfo objects.
        """
        try:
            data = self._call_api("/get_group_list", {})
            if data and isinstance(data, list):
                return [
                    QQGroupInfo(
                        group_id=g.get("group_id", 0),
                        group_name=g.get("group_name", ""),
                        member_count=g.get("member_count", 0),
                        max_member_count=g.get("max_member_count", 0),
                    )
                    for g in data
                ]
        except Exception as e:
            logger.error(f"Failed to get group list: {e}")
        return []

    def get_group_member_info(
        self,
        group_id: int,
        user_id: int,
        no_cache: bool = False,
    ) -> QQGroupMember | None:
        """Get group member information.

        Args:
            group_id: Group number.
            user_id: Member's QQ number.
            no_cache: Whether to bypass cache.

        Returns:
            QQGroupMember object or None.
        """
        try:
            data = self._call_api(
                "/get_group_member_info",
                {"group_id": group_id, "user_id": user_id, "no_cache": no_cache},
            )
            if data:
                return QQGroupMember(
                    group_id=data.get("group_id", group_id),
                    user_id=data.get("user_id", user_id),
                    nickname=data.get("nickname", ""),
                    card=data.get("card", ""),
                    sex=data.get("sex", "unknown"),
                    age=data.get("age", 0),
                    role=data.get("role", "member"),
                    title=data.get("title", ""),
                    join_time=data.get("join_time", 0),
                    last_sent_time=data.get("last_sent_time", 0),
                )
        except Exception as e:
            logger.error(f"Failed to get member info: {e}")
        return None

    def get_group_member_list(self, group_id: int) -> list[QQGroupMember]:
        """Get all members of a group.

        Args:
            group_id: Group number.

        Returns:
            List of QQGroupMember objects.
        """
        try:
            data = self._call_api("/get_group_member_list", {"group_id": group_id})
            if data and isinstance(data, list):
                return [
                    QQGroupMember(
                        group_id=group_id,
                        user_id=m.get("user_id", 0),
                        nickname=m.get("nickname", ""),
                        card=m.get("card", ""),
                        role=m.get("role", "member"),
                    )
                    for m in data
                ]
        except Exception as e:
            logger.error(f"Failed to get group member list: {e}")
        return []
