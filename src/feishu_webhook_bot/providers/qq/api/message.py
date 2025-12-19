"""OneBot11 message operations API.

This module provides message-related API operations:
- Delete/recall messages
- Get message details
- Send likes
- Forward messages
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from ....core.logger import get_logger
from ....core.provider import SendResult
from ..models import QQMessage

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class OneBotMessageMixin:
    """Mixin providing OneBot11 message operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self._parse_target(target) -> tuple[int | None, int | None]
    - self.logger
    """

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def _parse_target(self, target: str) -> tuple[int | None, int | None]:
        """Parse target. To be implemented by main class."""
        raise NotImplementedError

    def delete_msg(self, message_id: int) -> bool:
        """Recall/delete a message.

        Args:
            message_id: Message ID to delete.

        Returns:
            True if successful.
        """
        try:
            self._call_api("/delete_msg", {"message_id": message_id})
            return True
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            return False

    def get_msg(self, message_id: int) -> QQMessage | None:
        """Get message details by ID.

        Args:
            message_id: Message ID.

        Returns:
            QQMessage object or None if not found.
        """
        try:
            data = self._call_api("/get_msg", {"message_id": message_id})
            if data:
                return QQMessage(
                    message_id=data.get("message_id", message_id),
                    message_type=data.get("message_type", ""),
                    sender_id=data.get("sender", {}).get("user_id", 0),
                    sender_nickname=data.get("sender", {}).get("nickname", ""),
                    content=data.get("message", []),
                    time=data.get("time", 0),
                    group_id=data.get("group_id"),
                )
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
        return None

    def send_like(self, user_id: int, times: int = 1) -> bool:
        """Send likes to a user's profile.

        Args:
            user_id: Target QQ number.
            times: Number of likes (max 10 per day per user).

        Returns:
            True if successful.
        """
        try:
            self._call_api("/send_like", {"user_id": user_id, "times": min(times, 10)})
            return True
        except Exception as e:
            logger.error(f"Failed to send like to {user_id}: {e}")
            return False

    def send_forward_msg(
        self,
        target: str,
        messages: list[dict[str, Any]],
    ) -> SendResult:
        """Send a forward message (合并转发).

        Args:
            target: Target in format "private:QQ号" or "group:群号".
            messages: List of message nodes.

        Returns:
            SendResult with message ID.
        """
        message_id = str(uuid.uuid4())
        try:
            user_id, group_id = self._parse_target(target)

            payload: dict[str, Any] = {"messages": messages}
            if user_id:
                payload["message_type"] = "private"
                payload["user_id"] = user_id
            elif group_id:
                payload["message_type"] = "group"
                payload["group_id"] = group_id
            else:
                return SendResult.fail("Invalid target format")

            result = self._call_api("/send_forward_msg", payload)
            return SendResult.ok(str(result.get("message_id", message_id)), result)
        except Exception as e:
            return SendResult.fail(str(e))

    def get_forward_msg(self, forward_id: str) -> list[dict[str, Any]]:
        """Get forward message content.

        Args:
            forward_id: Forward message ID.

        Returns:
            List of message nodes.
        """
        try:
            data = self._call_api("/get_forward_msg", {"id": forward_id})
            return data.get("message", []) if data else []
        except Exception as e:
            logger.error(f"Failed to get forward message: {e}")
            return []
