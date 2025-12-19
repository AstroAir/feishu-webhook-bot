"""OneBot11 system status API.

This module provides system status operations:
- Get bot status
- Get version info
- Check capabilities
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger

logger = get_logger(__name__)


class OneBotSystemMixin:
    """Mixin providing OneBot11 system status operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self.logger
    """

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def get_status(self) -> dict[str, Any]:
        """Get bot running status.

        Returns:
            Status dict with online and good fields.
        """
        try:
            return self._call_api("/get_status", {}) or {}
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"online": False, "good": False}

    def get_version_info(self) -> dict[str, Any]:
        """Get OneBot implementation version info.

        Returns:
            Version info dict.
        """
        try:
            return self._call_api("/get_version_info", {}) or {}
        except Exception as e:
            logger.error(f"Failed to get version info: {e}")
            return {}

    def can_send_image(self) -> bool:
        """Check if bot can send images.

        Returns:
            True if can send images.
        """
        try:
            data = self._call_api("/can_send_image", {})
            return data.get("yes", False) if data else False
        except Exception:
            return False

    def can_send_record(self) -> bool:
        """Check if bot can send voice messages.

        Returns:
            True if can send voice.
        """
        try:
            data = self._call_api("/can_send_record", {})
            return data.get("yes", False) if data else False
        except Exception:
            return False
