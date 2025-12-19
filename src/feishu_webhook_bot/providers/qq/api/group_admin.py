"""OneBot11 group administration API.

This module provides group management operations:
- Kick members
- Ban/mute members
- Set/unset admins
- Set member cards
- Set group name
- Leave group
- Set special titles
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger

logger = get_logger(__name__)


class OneBotGroupAdminMixin:
    """Mixin providing OneBot11 group administration operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self.logger
    """

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def set_group_kick(
        self,
        group_id: int,
        user_id: int,
        reject_add_request: bool = False,
    ) -> bool:
        """Kick a member from group.

        Args:
            group_id: Group number.
            user_id: Member to kick.
            reject_add_request: Whether to reject future join requests.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_kick",
                {
                    "group_id": group_id,
                    "user_id": user_id,
                    "reject_add_request": reject_add_request,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to kick user {user_id} from group {group_id}: {e}")
            return False

    def set_group_ban(
        self,
        group_id: int,
        user_id: int,
        duration: int = 1800,
    ) -> bool:
        """Ban/mute a group member.

        Args:
            group_id: Group number.
            user_id: Member to ban.
            duration: Ban duration in seconds (0 to unban).

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_ban",
                {"group_id": group_id, "user_id": user_id, "duration": duration},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to ban user {user_id}: {e}")
            return False

    def set_group_whole_ban(self, group_id: int, enable: bool = True) -> bool:
        """Enable/disable whole group mute.

        Args:
            group_id: Group number.
            enable: Whether to enable mute.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_whole_ban",
                {"group_id": group_id, "enable": enable},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set whole ban for group {group_id}: {e}")
            return False

    def set_group_admin(
        self,
        group_id: int,
        user_id: int,
        enable: bool = True,
    ) -> bool:
        """Set/unset group admin.

        Args:
            group_id: Group number.
            user_id: Member to set as admin.
            enable: Whether to set as admin.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_admin",
                {"group_id": group_id, "user_id": user_id, "enable": enable},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set admin for user {user_id}: {e}")
            return False

    def set_group_card(self, group_id: int, user_id: int, card: str = "") -> bool:
        """Set group member's card/nickname.

        Args:
            group_id: Group number.
            user_id: Member's QQ number.
            card: New card name (empty to clear).

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_card",
                {"group_id": group_id, "user_id": user_id, "card": card},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set card for user {user_id}: {e}")
            return False

    def set_group_name(self, group_id: int, group_name: str) -> bool:
        """Set group name.

        Args:
            group_id: Group number.
            group_name: New group name.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_name",
                {"group_id": group_id, "group_name": group_name},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set group name: {e}")
            return False

    def set_group_leave(self, group_id: int, is_dismiss: bool = False) -> bool:
        """Leave a group.

        Args:
            group_id: Group number.
            is_dismiss: Whether to dismiss group (if owner).

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_leave",
                {"group_id": group_id, "is_dismiss": is_dismiss},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to leave group {group_id}: {e}")
            return False

    def set_group_special_title(
        self,
        group_id: int,
        user_id: int,
        special_title: str = "",
        duration: int = -1,
    ) -> bool:
        """Set member's special title.

        Args:
            group_id: Group number.
            user_id: Member's QQ number.
            special_title: Special title (empty to clear).
            duration: Duration in seconds (-1 for permanent).

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_special_title",
                {
                    "group_id": group_id,
                    "user_id": user_id,
                    "special_title": special_title,
                    "duration": duration,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set special title: {e}")
            return False
