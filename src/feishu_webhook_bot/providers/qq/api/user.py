"""OneBot11 user information API.

This module provides user-related API operations:
- Get login info (bot info)
- Get stranger info
- Get friend list
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger
from ..models import QQUserInfo

logger = get_logger(__name__)


class OneBotUserMixin:
    """Mixin providing OneBot11 user information operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self._login_info: dict | None
    - self.logger
    """

    _login_info: dict[str, Any] | None

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def get_login_info(self) -> dict[str, Any]:
        """Get bot's login information.

        Returns:
            Dict with user_id and nickname.
        """
        if self._login_info:
            return self._login_info

        try:
            data = self._call_api("/get_login_info", {})
            self._login_info = data or {}
            return self._login_info
        except Exception as e:
            logger.error(f"Failed to get login info: {e}")
            return {}

    def get_stranger_info(self, user_id: int, no_cache: bool = False) -> QQUserInfo | None:
        """Get stranger/user information.

        Args:
            user_id: QQ number.
            no_cache: Whether to bypass cache.

        Returns:
            QQUserInfo object or None.
        """
        try:
            data = self._call_api(
                "/get_stranger_info",
                {"user_id": user_id, "no_cache": no_cache},
            )
            if data:
                return QQUserInfo(
                    user_id=data.get("user_id", user_id),
                    nickname=data.get("nickname", ""),
                    sex=data.get("sex", "unknown"),
                    age=data.get("age", 0),
                )
        except Exception as e:
            logger.error(f"Failed to get stranger info for {user_id}: {e}")
        return None

    def get_friend_list(self) -> list[QQUserInfo]:
        """Get bot's friend list.

        Returns:
            List of QQUserInfo objects.
        """
        try:
            data = self._call_api("/get_friend_list", {})
            if data and isinstance(data, list):
                return [
                    QQUserInfo(
                        user_id=f.get("user_id", 0),
                        nickname=f.get("nickname", ""),
                        remark=f.get("remark", ""),
                    )
                    for f in data
                ]
        except Exception as e:
            logger.error(f"Failed to get friend list: {e}")
        return []
