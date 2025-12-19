"""User and chat info API operations for Feishu.

This module provides user and chat information queries:
- Get user information
- Get chat/group information
- Get chat members
- Get bot information
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from ....core.logger import get_logger
from .models import FeishuAPIError

if TYPE_CHECKING:
    pass

logger = get_logger("feishu_api.user")


class FeishuUserMixin:
    """Mixin providing user/chat info functionality for Feishu API.

    This mixin should be used with a class that has:
    - self._ensure_client() -> httpx.AsyncClient
    - self.get_tenant_access_token() -> str
    """

    # API endpoints
    GET_USER_URL = "/contact/v3/users/{user_id}"
    GET_CHAT_URL = "/im/v1/chats/{chat_id}"
    GET_CHAT_MEMBERS_URL = "/im/v1/chats/{chat_id}/members"
    GET_BOT_INFO_URL = "/bot/v3/info"

    def _ensure_client(self) -> Any:
        """Ensure HTTP client is initialized. To be implemented by main class."""
        raise NotImplementedError

    async def get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """Get tenant access token. To be implemented by main class."""
        raise NotImplementedError

    async def get_user_info(
        self,
        user_id: str,
        user_id_type: Literal["open_id", "user_id", "union_id"] = "open_id",
    ) -> dict[str, Any]:
        """Get user information.

        Args:
            user_id: User ID.
            user_id_type: Type of user_id.

        Returns:
            User information dict with name, avatar, email, etc.

        Raises:
            FeishuAPIError: If API call fails.

        Example:
            ```python
            user = await api.get_user_info("ou_xxx")
            print(f"Name: {user.get('name')}")
            print(f"Email: {user.get('email')}")
            ```
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.GET_USER_URL.format(user_id=user_id)
        response = await client.get(
            url,
            params={"user_id_type": user_id_type},
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        return data.get("data", {}).get("user", {})

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        """Get chat/group information.

        Args:
            chat_id: Chat ID.

        Returns:
            Chat information with name, description, owner, etc.

        Raises:
            FeishuAPIError: If API call fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.GET_CHAT_URL.format(chat_id=chat_id)
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        return data.get("data", {})

    async def get_chat_members(
        self,
        chat_id: str,
        page_size: int = 100,
        page_token: str = "",
    ) -> tuple[list[dict[str, Any]], str]:
        """Get chat members list.

        Args:
            chat_id: Chat ID.
            page_size: Number of members per page (max 100).
            page_token: Token for pagination.

        Returns:
            Tuple of (members_list, next_page_token).

        Raises:
            FeishuAPIError: If API call fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.GET_CHAT_MEMBERS_URL.format(chat_id=chat_id)
        params: dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        response = await client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        result = data.get("data", {})
        members = result.get("items", [])
        next_token = result.get("page_token", "")

        return members, next_token

    async def get_bot_info(self) -> dict[str, Any]:
        """Get bot information.

        Returns:
            Bot info with app_name, avatar_url, open_id, etc.

        Raises:
            FeishuAPIError: If API call fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        response = await client.get(
            self.GET_BOT_INFO_URL,
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        return data.get("bot", {})
