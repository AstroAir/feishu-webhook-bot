"""NapCat file operations.

This module provides file-related operations:
- Get file info
- Private file URL
- Group file operations
"""

from __future__ import annotations

from typing import Any

from ....core.logger import get_logger

logger = get_logger(__name__)


class NapcatFileMixin:
    """Mixin providing NapCat file operations.

    This mixin should be used with a class that has:
    - self._call_api(endpoint, payload) -> Any
    - self.logger
    """

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API. To be implemented by main class."""
        raise NotImplementedError

    def get_file(self, file_id: str) -> dict[str, Any]:
        """Get file information.

        Args:
            file_id: File ID.

        Returns:
            File info dict with file, url, file_size, file_name.
        """
        try:
            return self._call_api("/get_file", {"file_id": file_id}) or {}
        except Exception as e:
            logger.error(f"Failed to get file: {e}")
            return {}

    def get_private_file_url(self, file_id: str) -> str:
        """Get private file download URL.

        Args:
            file_id: File ID from message.

        Returns:
            File download URL or empty string.
        """
        try:
            data = self._call_api("/get_private_file_url", {"file_id": file_id})
            return data.get("url", "") if data else ""
        except Exception as e:
            logger.error(f"Failed to get private file URL: {e}")
            return ""

    def move_group_file(
        self,
        group_id: int,
        file_id: str,
        parent_dir_id: str,
    ) -> bool:
        """Move a file within group files.

        Args:
            group_id: Group number.
            file_id: File ID to move.
            parent_dir_id: Target directory ID.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/move_group_file",
                {
                    "group_id": group_id,
                    "file_id": file_id,
                    "parent_dir_id": parent_dir_id,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to move group file: {e}")
            return False

    def rename_group_file(
        self,
        group_id: int,
        file_id: str,
        new_name: str,
    ) -> bool:
        """Rename a group file.

        Args:
            group_id: Group number.
            file_id: File ID to rename.
            new_name: New file name.

        Returns:
            True if successful.
        """
        try:
            self._call_api(
                "/rename_group_file",
                {
                    "group_id": group_id,
                    "file_id": file_id,
                    "new_name": new_name,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to rename group file: {e}")
            return False

    def trans_group_file(
        self,
        group_id: int,
        file_id: str,
    ) -> str:
        """Transfer group file to personal storage.

        Args:
            group_id: Group number.
            file_id: File ID to transfer.

        Returns:
            New file ID in personal storage or empty string.
        """
        try:
            data = self._call_api(
                "/trans_group_file",
                {"group_id": group_id, "file_id": file_id},
            )
            return data.get("file_id", "") if data else ""
        except Exception as e:
            logger.error(f"Failed to transfer group file: {e}")
            return ""
