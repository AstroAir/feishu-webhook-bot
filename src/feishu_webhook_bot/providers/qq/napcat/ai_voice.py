"""NapCat AI voice functionality.

This module provides AI voice-related operations:
- Get AI characters
- Get AI voice record
- Send group AI record
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ....core.logger import get_logger
from ....core.provider import SendResult

if TYPE_CHECKING:
    from ..config import NapcatProviderConfig

logger = get_logger(__name__)


class NapcatAIVoiceMixin:
    """Mixin providing NapCat AI voice operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self.config: NapcatProviderConfig
    - self.logger
    """

    config: NapcatProviderConfig

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def get_ai_characters(self, group_id: int) -> list[dict[str, Any]]:
        """Get available AI voice characters.

        Args:
            group_id: Group number (required for API).

        Returns:
            List of character info dicts.
        """
        if not self.config.enable_ai_voice:
            return []

        try:
            data = self._call_api("/get_ai_characters", {"group_id": group_id})
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to get AI characters: {e}")
            return []

    def get_ai_record(
        self,
        character: str,
        group_id: int,
        text: str,
    ) -> str:
        """Convert text to AI voice.

        Args:
            character: AI character ID.
            group_id: Group number.
            text: Text to convert.

        Returns:
            Voice file URL or empty string.
        """
        if not self.config.enable_ai_voice:
            return ""

        try:
            data = self._call_api(
                "/get_ai_record",
                {"character": character, "group_id": group_id, "text": text},
            )
            return data.get("data", "") if data else ""
        except Exception as e:
            logger.error(f"Failed to get AI record: {e}")
            return ""

    def send_group_ai_record(
        self,
        group_id: int,
        character: str,
        text: str,
    ) -> SendResult:
        """Send AI voice message to group.

        Args:
            group_id: Group number.
            character: AI character ID.
            text: Text to convert to voice.

        Returns:
            SendResult with message ID.
        """
        if not self.config.enable_ai_voice:
            return SendResult.fail("AI voice not enabled")

        try:
            data = self._call_api(
                "/send_group_ai_record",
                {"group_id": group_id, "character": character, "text": text},
            )
            msg_id = data.get("message_id", "") if data else ""
            return SendResult.ok(str(msg_id), data)
        except Exception as e:
            return SendResult.fail(str(e))
