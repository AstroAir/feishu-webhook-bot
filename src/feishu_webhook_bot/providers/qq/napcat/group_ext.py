"""NapCat group extension functionality.

This module provides extended group operations:
- Group announcements
- Group sign-in
- Online status
- Profile operations
- Extended group info
- Group honor
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger
from ..models import OnlineStatus

logger = get_logger(__name__)


class NapcatGroupExtMixin:
    """Mixin providing NapCat group extension operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self.logger
    """

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def get_group_notice(self, group_id: int) -> list[dict[str, Any]]:
        """Get group announcements.

        Args:
            group_id: Group number.

        Returns:
            List of announcement dicts with sender_id, publish_time, content.
        """
        try:
            data = self._call_api("/get_group_notice", {"group_id": group_id})
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to get group notice: {e}")
            return []

    def send_group_notice(
        self,
        group_id: int,
        content: str,
        image: str = "",
    ) -> bool:
        """Send a group announcement.

        Args:
            group_id: Group number.
            content: Announcement content.
            image: Optional image URL or file path.

        Returns:
            True if successful.
        """
        try:
            payload: dict[str, Any] = {"group_id": group_id, "content": content}
            if image:
                payload["image"] = image
            self._call_api("/_send_group_notice", payload)
            return True
        except Exception as e:
            logger.error(f"Failed to send group notice: {e}")
            return False

    def del_group_notice(self, group_id: int, notice_id: str) -> bool:
        """Delete a group announcement.

        Args:
            group_id: Group number.
            notice_id: Announcement ID to delete.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/_del_group_notice",
                {"group_id": group_id, "notice_id": notice_id},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete group notice: {e}")
            return False

    def set_group_sign(self, group_id: int) -> bool:
        """Sign in to group (群签到).

        Args:
            group_id: Group number.

        Returns:
            True if successful.
        """
        try:
            self._call_api("/set_group_sign", {"group_id": str(group_id)})
            return True
        except Exception as e:
            logger.error(f"Failed to sign in group: {e}")
            return False

    def set_online_status(
        self,
        status: OnlineStatus | int,
        ext_status: int = 0,
        battery_status: int = 0,
    ) -> bool:
        """Set bot's online status.

        Args:
            status: Online status code.
            ext_status: Extended status.
            battery_status: Battery level.

        Returns:
            True if successful.
        """
        try:
            status_val = status.value if isinstance(status, OnlineStatus) else status
            self._call_api(
                "/set_online_status",
                {
                    "status": status_val,
                    "ext_status": ext_status,
                    "battery_status": battery_status,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set online status: {e}")
            return False

    def set_qq_avatar(self, file: str) -> bool:
        """Set bot's QQ avatar.

        Args:
            file: Image file path or URL.

        Returns:
            True if successful.
        """
        try:
            self._call_api("/set_qq_avatar", {"file": file})
            return True
        except Exception as e:
            logger.error(f"Failed to set avatar: {e}")
            return False

    def get_profile_like(self) -> dict[str, Any]:
        """Get profile likes information.

        Returns:
            Profile like info dict.
        """
        try:
            return self._call_api("/get_profile_like", {}) or {}
        except Exception as e:
            logger.error(f"Failed to get profile like: {e}")
            return {}

    def set_input_status(self, user_id: int, event_type: int = 1) -> bool:
        """Set input status (typing indicator).

        Args:
            user_id: Target user QQ number.
            event_type: Status type (1=typing, 0=stop).

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_input_status",
                {"user_id": user_id, "event_type": event_type},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set input status: {e}")
            return False

    def get_cookies(self, domain: str = "") -> str:
        """Get QQ cookies for a domain.

        Args:
            domain: Target domain (empty for default).

        Returns:
            Cookie string.
        """
        try:
            data = self._call_api("/get_cookies", {"domain": domain})
            return data.get("cookies", "") if data else ""
        except Exception as e:
            logger.error(f"Failed to get cookies: {e}")
            return ""

    def get_clientkey(self) -> str:
        """Get client key.

        Returns:
            Client key string.
        """
        try:
            data = self._call_api("/.get_clientkey", {})
            return data.get("clientkey", "") if data else ""
        except Exception as e:
            logger.error(f"Failed to get clientkey: {e}")
            return ""

    def get_group_info_ex(self, group_id: int) -> dict[str, Any]:
        """Get extended group information.

        Args:
            group_id: Group number.

        Returns:
            Extended group info dict.
        """
        try:
            return self._call_api("/get_group_info_ex", {"group_id": group_id}) or {}
        except Exception as e:
            logger.error(f"Failed to get extended group info: {e}")
            return {}

    def set_group_portrait(self, group_id: int, file: str) -> bool:
        """Set group avatar/portrait.

        Args:
            group_id: Group number.
            file: Image file path or URL.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_portrait",
                {"group_id": group_id, "file": file},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set group portrait: {e}")
            return False

    def get_group_honor_info(
        self,
        group_id: int,
        honor_type: str = "all",
    ) -> dict[str, Any]:
        """Get group honor information.

        Args:
            group_id: Group number.
            honor_type: Honor type (talkative, performer, legend, strong_newbie, emotion, all).

        Returns:
            Group honor info dict.
        """
        try:
            return (
                self._call_api(
                    "/get_group_honor_info",
                    {"group_id": group_id, "type": honor_type},
                )
                or {}
            )
        except Exception as e:
            logger.error(f"Failed to get group honor info: {e}")
            return {}

    def get_group_at_all_remain(self, group_id: int) -> dict[str, Any]:
        """Get remaining @all count for today.

        Args:
            group_id: Group number.

        Returns:
            Dict with can_at_all, remain_at_all_count_for_group, remain_at_all_count_for_uin.
        """
        try:
            return self._call_api("/get_group_at_all_remain", {"group_id": group_id}) or {}
        except Exception as e:
            logger.error(f"Failed to get @all remain: {e}")
            return {}
