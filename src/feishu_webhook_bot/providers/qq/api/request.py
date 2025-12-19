"""OneBot11 request handling API.

This module provides request handling operations:
- Handle friend add requests
- Handle group add/invite requests
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger

logger = get_logger(__name__)


class OneBotRequestMixin:
    """Mixin providing OneBot11 request handling operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self.logger
    """

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def set_friend_add_request(
        self,
        flag: str,
        approve: bool = True,
        remark: str = "",
    ) -> bool:
        """Handle friend add request.

        Args:
            flag: Request flag from event.
            approve: Whether to approve.
            remark: Friend remark (if approved).

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_friend_add_request",
                {"flag": flag, "approve": approve, "remark": remark},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to handle friend request: {e}")
            return False

    def set_group_add_request(
        self,
        flag: str,
        sub_type: str,
        approve: bool = True,
        reason: str = "",
    ) -> bool:
        """Handle group add/invite request.

        Args:
            flag: Request flag from event.
            sub_type: "add" or "invite".
            approve: Whether to approve.
            reason: Rejection reason (if not approved).

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_group_add_request",
                {
                    "flag": flag,
                    "sub_type": sub_type,
                    "approve": approve,
                    "reason": reason,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to handle group request: {e}")
            return False
