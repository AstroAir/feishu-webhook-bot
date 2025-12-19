"""NapCat message extension functionality.

This module provides extended message operations:
- Emoji reactions
- Mark as read
- Message history
- Essence messages
- Message forwarding
- OCR
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger
from ....core.provider import SendResult

logger = get_logger(__name__)


class NapcatMessageExtMixin:
    """Mixin providing NapCat message extension operations.

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

    def set_msg_emoji_like(self, message_id: int, emoji_id: str) -> bool:
        """React to a message with emoji.

        Args:
            message_id: Message ID.
            emoji_id: Emoji ID.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/set_msg_emoji_like",
                {"message_id": message_id, "emoji_id": emoji_id},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set emoji reaction: {e}")
            return False

    def mark_msg_as_read(self, target: str) -> bool:
        """Mark messages as read.

        Args:
            target: "private:QQ号" or "group:群号".

        Returns:
            True if successful.
        """
        try:
            user_id, group_id = self._parse_target(target)
            if user_id:
                self._call_api("/mark_private_msg_as_read", {"user_id": user_id})
            elif group_id:
                self._call_api("/mark_group_msg_as_read", {"group_id": group_id})
            else:
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return False

    def get_group_msg_history(
        self,
        group_id: int,
        message_seq: int = 0,
        count: int = 20,
    ) -> list[dict[str, Any]]:
        """Get group message history.

        Args:
            group_id: Group number.
            message_seq: Starting message sequence (0 for latest).
            count: Number of messages to retrieve.

        Returns:
            List of message dicts.
        """
        try:
            data = self._call_api(
                "/get_group_msg_history",
                {"group_id": group_id, "message_seq": message_seq, "count": count},
            )
            return data.get("messages", []) if data else []
        except Exception as e:
            logger.error(f"Failed to get group history: {e}")
            return []

    def get_friend_msg_history(
        self,
        user_id: int,
        message_seq: int = 0,
        count: int = 20,
    ) -> list[dict[str, Any]]:
        """Get private message history.

        Args:
            user_id: Friend's QQ number.
            message_seq: Starting message sequence (0 for latest).
            count: Number of messages to retrieve.

        Returns:
            List of message dicts.
        """
        try:
            data = self._call_api(
                "/get_friend_msg_history",
                {"user_id": user_id, "message_seq": message_seq, "count": count},
            )
            return data.get("messages", []) if data else []
        except Exception as e:
            logger.error(f"Failed to get friend history: {e}")
            return []

    def get_essence_msg_list(self, group_id: int) -> list[dict[str, Any]]:
        """Get essence/pinned messages in a group.

        Args:
            group_id: Group number.

        Returns:
            List of essence message dicts.
        """
        try:
            data = self._call_api("/get_essence_msg_list", {"group_id": group_id})
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to get essence messages: {e}")
            return []

    def set_essence_msg(self, message_id: int) -> bool:
        """Set a message as essence/pinned.

        Args:
            message_id: Message ID to set as essence.

        Returns:
            True if successful.
        """
        try:
            self._call_api("/set_essence_msg", {"message_id": message_id})
            return True
        except Exception as e:
            logger.error(f"Failed to set essence message: {e}")
            return False

    def delete_essence_msg(self, message_id: int) -> bool:
        """Remove a message from essence/pinned.

        Args:
            message_id: Message ID to remove from essence.

        Returns:
            True if successful.
        """
        try:
            self._call_api("/delete_essence_msg", {"message_id": message_id})
            return True
        except Exception as e:
            logger.error(f"Failed to delete essence message: {e}")
            return False

    def forward_friend_single_msg(
        self,
        message_id: int,
        user_id: int,
    ) -> SendResult:
        """Forward a single message to a friend.

        Args:
            message_id: Message ID to forward.
            user_id: Target friend QQ number.

        Returns:
            SendResult with new message ID.
        """
        try:
            data = self._call_api(
                "/forward_friend_single_msg",
                {"message_id": message_id, "user_id": user_id},
            )
            new_id = data.get("message_id", "") if data else ""
            return SendResult.ok(str(new_id), data)
        except Exception as e:
            return SendResult.fail(str(e))

    def forward_group_single_msg(
        self,
        message_id: int,
        group_id: int,
    ) -> SendResult:
        """Forward a single message to a group.

        Args:
            message_id: Message ID to forward.
            group_id: Target group number.

        Returns:
            SendResult with new message ID.
        """
        try:
            data = self._call_api(
                "/forward_group_single_msg",
                {"message_id": message_id, "group_id": group_id},
            )
            new_id = data.get("message_id", "") if data else ""
            return SendResult.ok(str(new_id), data)
        except Exception as e:
            return SendResult.fail(str(e))

    def ocr_image(self, image: str) -> list[dict[str, Any]]:
        """Perform OCR on an image.

        Args:
            image: Image URL or file path.

        Returns:
            List of OCR result dicts with text and coordinates.
        """
        try:
            data = self._call_api("/ocr_image", {"image": image})
            if data:
                return data.get("texts", []) if isinstance(data, dict) else data
            return []
        except Exception as e:
            logger.error(f"Failed to OCR image: {e}")
            return []

    def fetch_custom_face(self, count: int = 48) -> list[dict[str, Any]]:
        """Fetch custom face/emoji list.

        Args:
            count: Number of faces to fetch (max 48).

        Returns:
            List of custom face info dicts.
        """
        try:
            data = self._call_api("/fetch_custom_face", {"count": min(count, 48)})
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch custom face: {e}")
            return []

    def fetch_emoji_like(
        self,
        message_id: int,
        emoji_id: str,
        emoji_type: str = "1",
    ) -> list[dict[str, Any]]:
        """Fetch users who reacted with an emoji.

        Args:
            message_id: Message ID.
            emoji_id: Emoji ID.
            emoji_type: Emoji type.

        Returns:
            List of user info dicts.
        """
        try:
            data = self._call_api(
                "/fetch_emoji_like",
                {
                    "message_id": message_id,
                    "emoji_id": emoji_id,
                    "emoji_type": emoji_type,
                },
            )
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch emoji like: {e}")
            return []

    def translate_en2zh(self, words: list[str]) -> list[str]:
        """Translate English to Chinese (NapCat feature).

        Args:
            words: List of English words/phrases.

        Returns:
            List of Chinese translations.
        """
        try:
            data = self._call_api("/translate_en2zh", {"words": words})
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to translate: {e}")
            return []
