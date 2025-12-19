"""Chat management API operations for Feishu.

This module provides chat/group management operations:
- Create chats
- Update chat settings
- Delete/dissolve chats
- Add/remove chat members
- Check membership
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from ....core.logger import get_logger
from .models import FeishuAPIError

if TYPE_CHECKING:
    pass

logger = get_logger("feishu_api.chat")


class FeishuChatMixin:
    """Mixin providing chat management functionality for Feishu API.

    This mixin should be used with a class that has:
    - self._ensure_client() -> httpx.AsyncClient
    - self.get_tenant_access_token() -> str
    """

    # API endpoints
    CREATE_CHAT_URL = "/im/v1/chats"
    UPDATE_CHAT_URL = "/im/v1/chats/{chat_id}"
    DELETE_CHAT_URL = "/im/v1/chats/{chat_id}"
    ADD_CHAT_MEMBERS_URL = "/im/v1/chats/{chat_id}/members"
    REMOVE_CHAT_MEMBERS_URL = "/im/v1/chats/{chat_id}/members"
    IS_MEMBER_URL = "/im/v1/chats/{chat_id}/members/is_in_chat"

    def _ensure_client(self) -> Any:
        """Ensure HTTP client is initialized. To be implemented by main class."""
        raise NotImplementedError

    async def get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """Get tenant access token. To be implemented by main class."""
        raise NotImplementedError

    async def create_chat(
        self,
        name: str,
        description: str = "",
        user_ids: list[str] | None = None,
        owner_id: str | None = None,
        chat_mode: Literal["group", "topic"] = "group",
        chat_type: Literal["private", "public"] = "private",
        user_id_type: Literal["open_id", "user_id", "union_id"] = "open_id",
    ) -> dict[str, Any]:
        """Create a new chat/group.

        Args:
            name: Chat name.
            description: Chat description.
            user_ids: List of user IDs to add.
            owner_id: Owner user ID.
            chat_mode: "group" or "topic".
            chat_type: "private" or "public".
            user_id_type: Type of user IDs.

        Returns:
            Created chat info with chat_id.

        Raises:
            FeishuAPIError: If creation fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        body: dict[str, Any] = {
            "name": name,
            "chat_mode": chat_mode,
            "chat_type": chat_type,
        }
        if description:
            body["description"] = description
        if user_ids:
            body["user_id_list"] = user_ids
        if owner_id:
            body["owner_id"] = owner_id

        response = await client.post(
            self.CREATE_CHAT_URL,
            params={"user_id_type": user_id_type},
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        logger.info("Chat created: %s", data.get("data", {}).get("chat_id"))
        return data.get("data", {})

    async def update_chat(
        self,
        chat_id: str,
        name: str | None = None,
        description: str | None = None,
        owner_id: str | None = None,
    ) -> bool:
        """Update chat settings.

        Args:
            chat_id: Chat ID to update.
            name: New chat name (optional).
            description: New description (optional).
            owner_id: New owner ID (optional).

        Returns:
            True if update succeeded.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if owner_id is not None:
            body["owner_id"] = owner_id

        if not body:
            return True  # Nothing to update

        url = self.UPDATE_CHAT_URL.format(chat_id=chat_id)
        response = await client.put(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )

        data = response.json()
        if data.get("code") != 0:
            logger.error("Failed to update chat: %s", data.get("msg"))
            return False

        return True

    async def delete_chat(self, chat_id: str) -> bool:
        """Delete/dissolve a chat.

        Args:
            chat_id: Chat ID to delete.

        Returns:
            True if deletion succeeded.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.DELETE_CHAT_URL.format(chat_id=chat_id)
        response = await client.delete(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data.get("code") != 0:
            logger.error("Failed to delete chat: %s", data.get("msg"))
            return False

        logger.info("Chat deleted: %s", chat_id)
        return True

    async def add_chat_members(
        self,
        chat_id: str,
        user_ids: list[str],
        member_id_type: Literal["open_id", "user_id", "union_id"] = "open_id",
    ) -> dict[str, Any]:
        """Add members to a chat.

        Args:
            chat_id: Chat ID.
            user_ids: List of user IDs to add.
            member_id_type: Type of user IDs.

        Returns:
            Result with invalid_id_list if any IDs failed.

        Raises:
            FeishuAPIError: If API call fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.ADD_CHAT_MEMBERS_URL.format(chat_id=chat_id)
        response = await client.post(
            url,
            params={"member_id_type": member_id_type},
            headers={"Authorization": f"Bearer {token}"},
            json={"id_list": user_ids},
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        return data.get("data", {})

    async def remove_chat_members(
        self,
        chat_id: str,
        user_ids: list[str],
        member_id_type: Literal["open_id", "user_id", "union_id"] = "open_id",
    ) -> dict[str, Any]:
        """Remove members from a chat.

        Args:
            chat_id: Chat ID.
            user_ids: List of user IDs to remove.
            member_id_type: Type of user IDs.

        Returns:
            Result with invalid_id_list if any IDs failed.

        Raises:
            FeishuAPIError: If API call fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.REMOVE_CHAT_MEMBERS_URL.format(chat_id=chat_id)
        response = await client.delete(
            url,
            params={"member_id_type": member_id_type},
            headers={"Authorization": f"Bearer {token}"},
            json={"id_list": user_ids},
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        return data.get("data", {})

    async def is_member(
        self,
        chat_id: str,
    ) -> bool:
        """Check if bot is a member of the chat.

        Args:
            chat_id: Chat ID to check.

        Returns:
            True if bot is a member.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.IS_MEMBER_URL.format(chat_id=chat_id)
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data.get("code") != 0:
            return False

        return data.get("data", {}).get("is_in_chat", False)
