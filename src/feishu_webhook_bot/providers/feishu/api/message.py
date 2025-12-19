"""Message API operations for Feishu.

This module provides message-related API operations:
- Send messages to users/chats
- Reply to messages
- Recall/delete messages
- Get message details
- Update messages
- Forward messages
- List messages in a chat
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from ....core.logger import get_logger
from .models import FeishuAPIError, MessageSendResult, ReceiveIdType

if TYPE_CHECKING:
    pass

logger = get_logger("feishu_api.message")


class FeishuMessageMixin:
    """Mixin providing message API functionality for Feishu.

    This mixin should be used with a class that has:
    - self._ensure_client() -> httpx.AsyncClient
    - self.get_tenant_access_token() -> str
    """

    # API endpoints
    SEND_MESSAGE_URL = "/im/v1/messages"
    REPLY_MESSAGE_URL = "/im/v1/messages/{message_id}/reply"
    GET_MESSAGE_URL = "/im/v1/messages/{message_id}"
    RECALL_MESSAGE_URL = "/im/v1/messages/{message_id}"
    LIST_MESSAGES_URL = "/im/v1/messages"
    UPDATE_MESSAGE_URL = "/im/v1/messages/{message_id}"
    FORWARD_MESSAGE_URL = "/im/v1/messages/{message_id}/forward"
    GET_MESSAGE_RESOURCE_URL = "/im/v1/messages/{message_id}/resources/{file_key}"

    def _ensure_client(self) -> Any:
        """Ensure HTTP client is initialized. To be implemented by main class."""
        raise NotImplementedError

    async def get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """Get tenant access token. To be implemented by main class."""
        raise NotImplementedError

    async def send_message(
        self,
        receive_id: str,
        receive_id_type: ReceiveIdType,
        msg_type: str,
        content: dict[str, Any] | str,
        uuid: str | None = None,
    ) -> MessageSendResult:
        """Send a message to a user or chat.

        Args:
            receive_id: Target ID (open_id, chat_id, etc.).
            receive_id_type: Type of receive_id.
            msg_type: Message type (text, post, image, interactive, etc.).
            content: Message content (dict or JSON string).
            uuid: Optional deduplication UUID.

        Returns:
            MessageSendResult with success status and message_id.

        Raises:
            FeishuAPIError: If API call fails.

        Example:
            ```python
            # Send text message
            result = await api.send_message(
                receive_id="ou_xxx",
                receive_id_type="open_id",
                msg_type="text",
                content={"text": "Hello!"},
            )

            # Send to group chat
            result = await api.send_message(
                receive_id="oc_xxx",
                receive_id_type="chat_id",
                msg_type="text",
                content={"text": "Group message"},
            )
            ```
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        # Prepare content
        if isinstance(content, dict):
            content_str = json.dumps(content, ensure_ascii=False)
        else:
            content_str = content

        body = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content_str,
        }
        if uuid:
            body["uuid"] = uuid

        response = await client.post(
            self.SEND_MESSAGE_URL,
            params={"receive_id_type": receive_id_type},
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )

        data = response.json()
        if data.get("code") != 0:
            logger.error(
                "Failed to send message: code=%d, msg=%s",
                data.get("code"),
                data.get("msg"),
            )
            return MessageSendResult.fail(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        message_id = data.get("data", {}).get("message_id", "")
        logger.info("Message sent successfully: %s", message_id)
        return MessageSendResult.ok(message_id)

    async def reply_message(
        self,
        message_id: str,
        msg_type: str,
        content: dict[str, Any] | str,
        uuid: str | None = None,
    ) -> MessageSendResult:
        """Reply to a specific message.

        Args:
            message_id: ID of message to reply to.
            msg_type: Message type.
            content: Reply content.
            uuid: Optional deduplication UUID.

        Returns:
            MessageSendResult with success status and new message_id.

        Example:
            ```python
            result = await api.reply_message(
                message_id="om_xxx",
                msg_type="text",
                content={"text": "This is a reply"},
            )
            ```
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        if isinstance(content, dict):
            content_str = json.dumps(content, ensure_ascii=False)
        else:
            content_str = content

        body = {
            "msg_type": msg_type,
            "content": content_str,
        }
        if uuid:
            body["uuid"] = uuid

        url = self.REPLY_MESSAGE_URL.format(message_id=message_id)
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )

        data = response.json()
        if data.get("code") != 0:
            logger.error(
                "Failed to reply message: code=%d, msg=%s",
                data.get("code"),
                data.get("msg"),
            )
            return MessageSendResult.fail(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        new_message_id = data.get("data", {}).get("message_id", "")
        logger.info("Reply sent successfully: %s", new_message_id)
        return MessageSendResult.ok(new_message_id)

    async def recall_message(self, message_id: str) -> bool:
        """Recall (delete) a sent message.

        Args:
            message_id: ID of message to recall.

        Returns:
            True if recall succeeded.

        Note:
            Messages can only be recalled within 24 hours of sending.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.RECALL_MESSAGE_URL.format(message_id=message_id)
        response = await client.delete(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data.get("code") != 0:
            logger.error(
                "Failed to recall message: code=%d, msg=%s",
                data.get("code"),
                data.get("msg"),
            )
            return False

        logger.info("Message recalled: %s", message_id)
        return True

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """Get message details by ID.

        Args:
            message_id: Message ID.

        Returns:
            Message details including content, sender, etc.

        Raises:
            FeishuAPIError: If API call fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.GET_MESSAGE_URL.format(message_id=message_id)
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

        return data.get("data", {}).get("items", [{}])[0]

    async def list_messages(
        self,
        container_id: str,
        container_id_type: Literal["chat"] = "chat",
        start_time: str | None = None,
        end_time: str | None = None,
        sort_type: Literal["ByCreateTimeAsc", "ByCreateTimeDesc"] = "ByCreateTimeAsc",
        page_size: int = 20,
        page_token: str = "",
    ) -> tuple[list[dict[str, Any]], str, bool]:
        """List messages in a chat.

        Args:
            container_id: Chat ID.
            container_id_type: Container type (only "chat" supported).
            start_time: Start time (Unix timestamp string, optional).
            end_time: End time (Unix timestamp string, optional).
            sort_type: Sort order.
            page_size: Number of messages per page (max 50).
            page_token: Pagination token.

        Returns:
            Tuple of (messages_list, next_page_token, has_more).

        Raises:
            FeishuAPIError: If API call fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        params: dict[str, Any] = {
            "container_id_type": container_id_type,
            "container_id": container_id,
            "sort_type": sort_type,
            "page_size": page_size,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if page_token:
            params["page_token"] = page_token

        response = await client.get(
            self.LIST_MESSAGES_URL,
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
        items = result.get("items", [])
        next_token = result.get("page_token", "")
        has_more = result.get("has_more", False)

        return items, next_token, has_more

    async def update_message(
        self,
        message_id: str,
        msg_type: str,
        content: dict[str, Any] | str,
    ) -> bool:
        """Update a sent message.

        Args:
            message_id: ID of message to update.
            msg_type: Message type.
            content: New message content.

        Returns:
            True if update succeeded.

        Note:
            Only text and post messages can be updated.
            Messages can only be updated within 24 hours.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        if isinstance(content, dict):
            content_str = json.dumps(content, ensure_ascii=False)
        else:
            content_str = content

        url = self.UPDATE_MESSAGE_URL.format(message_id=message_id)
        response = await client.patch(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"msg_type": msg_type, "content": content_str},
        )

        data = response.json()
        if data.get("code") != 0:
            logger.error(
                "Failed to update message: code=%d, msg=%s",
                data.get("code"),
                data.get("msg"),
            )
            return False

        logger.info("Message updated: %s", message_id)
        return True

    async def forward_message(
        self,
        message_id: str,
        receive_id: str,
        receive_id_type: ReceiveIdType = "chat_id",
    ) -> MessageSendResult:
        """Forward a message to another chat.

        Args:
            message_id: ID of message to forward.
            receive_id: Target chat/user ID.
            receive_id_type: Type of receive_id.

        Returns:
            MessageSendResult with new message ID.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.FORWARD_MESSAGE_URL.format(message_id=message_id)
        response = await client.post(
            url,
            params={"receive_id_type": receive_id_type},
            headers={"Authorization": f"Bearer {token}"},
            json={"receive_id": receive_id},
        )

        data = response.json()
        if data.get("code") != 0:
            return MessageSendResult.fail(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        new_message_id = data.get("data", {}).get("message_id", "")
        return MessageSendResult.ok(new_message_id)

    async def get_message_resource(
        self,
        message_id: str,
        file_key: str,
        resource_type: Literal["image", "file"] = "file",
    ) -> bytes:
        """Download a file/image from a message.

        Args:
            message_id: Message ID containing the resource.
            file_key: File key of the resource.
            resource_type: Type of resource ("image" or "file").

        Returns:
            File content as bytes.

        Raises:
            FeishuAPIError: If download fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.GET_MESSAGE_RESOURCE_URL.format(message_id=message_id, file_key=file_key)
        response = await client.get(
            url,
            params={"type": resource_type},
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise FeishuAPIError(
                code=response.status_code,
                msg=f"Failed to download resource: {response.text}",
            )

        return response.content

    # Convenience methods

    async def send_text(
        self,
        receive_id: str,
        text: str,
        receive_id_type: ReceiveIdType = "chat_id",
    ) -> MessageSendResult:
        """Send a text message.

        Args:
            receive_id: Target ID.
            text: Text content.
            receive_id_type: Type of receive_id.

        Returns:
            MessageSendResult.
        """
        return await self.send_message(
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            msg_type="text",
            content={"text": text},
        )

    async def reply_text(
        self,
        message_id: str,
        text: str,
    ) -> MessageSendResult:
        """Reply with a text message.

        Args:
            message_id: ID of message to reply to.
            text: Reply text.

        Returns:
            MessageSendResult.
        """
        return await self.reply_message(
            message_id=message_id,
            msg_type="text",
            content={"text": text},
        )

    async def send_card(
        self,
        receive_id: str,
        card: dict[str, Any],
        receive_id_type: ReceiveIdType = "chat_id",
    ) -> MessageSendResult:
        """Send an interactive card.

        Args:
            receive_id: Target ID.
            card: Card content (use CardBuilder to create).
            receive_id_type: Type of receive_id.

        Returns:
            MessageSendResult.
        """
        return await self.send_message(
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            msg_type="interactive",
            content=card,
        )
