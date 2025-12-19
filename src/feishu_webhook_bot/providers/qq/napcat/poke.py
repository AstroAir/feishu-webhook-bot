"""NapCat poke functionality.

This module provides poke-related operations:
- Send poke
- Group poke
- Friend poke
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger

logger = get_logger(__name__)


class NapcatPokeMixin:
    """Mixin providing NapCat poke operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self.logger
    """

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def send_poke(self, user_id: int, group_id: int | None = None) -> bool:
        """Send poke (戳一戳).

        Args:
            user_id: Target QQ number.
            group_id: Group ID (None for private poke).

        Returns:
            True if successful.
        """
        try:
            payload: dict[str, Any] = {"user_id": user_id}
            if group_id:
                payload["group_id"] = group_id
            self._call_api("/send_poke", payload)
            return True
        except Exception as e:
            logger.error(f"Failed to send poke: {e}")
            return False

    def group_poke(self, group_id: int, user_id: int) -> bool:
        """Send group poke (群聊戳一戳).

        Args:
            group_id: Group number.
            user_id: Target QQ number.

        Returns:
            True if successful.
        """
        try:
            self._call_api("/group_poke", {"group_id": group_id, "user_id": user_id})
            return True
        except Exception as e:
            logger.error(f"Failed to send group poke: {e}")
            return False

    def friend_poke(self, user_id: int) -> bool:
        """Send friend poke (私聊戳一戳).

        Args:
            user_id: Target QQ number.

        Returns:
            True if successful.
        """
        try:
            self._call_api("/friend_poke", {"user_id": user_id})
            return True
        except Exception as e:
            logger.error(f"Failed to send friend poke: {e}")
            return False
