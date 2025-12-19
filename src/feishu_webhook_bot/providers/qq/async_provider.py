"""Async operations for NapcatProvider.

This module provides async versions of NapcatProvider methods.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from ...core.logger import get_logger
from ...core.message_tracker import MessageStatus
from ...core.provider import SendResult
from ..common.async_http import AsyncHTTPProviderMixin

logger = get_logger(__name__)


class AsyncNapcatMixin(AsyncHTTPProviderMixin):
    """Mixin providing async operations for NapcatProvider.

    This mixin adds async versions of all message sending and API methods.
    It should be used with NapcatProvider.
    """

    # These will be set by the main class
    config: Any
    _async_client: httpx.AsyncClient | None
    _message_tracker: Any
    name: str
    provider_type: str

    def _parse_target(self, target: str) -> tuple[int | None, int | None]:
        """Parse target. To be implemented by main class."""
        raise NotImplementedError

    async def async_connect(self) -> None:
        """Initialize async HTTP client."""
        if self._async_client is not None:
            return

        headers = {"Content-Type": "application/json"}
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"

        timeout = self.config.timeout or 10.0
        self._async_client = httpx.AsyncClient(
            timeout=timeout,
            headers=headers,
            base_url=self.config.http_url,
        )
        logger.debug("Async Napcat client connected")

    async def async_disconnect(self) -> None:
        """Close async HTTP client."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
            logger.debug("Async Napcat client disconnected")

    async def _async_call_api(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> Any:
        """Make async API call to OneBot endpoint.

        Args:
            endpoint: API endpoint path.
            payload: Request payload.

        Returns:
            Response data field.

        Raises:
            RuntimeError: If client not initialized.
            Exception: If request fails.
        """
        if not self._async_client:
            await self.async_connect()

        if not self._async_client:
            raise RuntimeError("Async client not initialized")

        response = await self._async_client.post(endpoint, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "ok":
            raise ValueError(f"API error: {result.get('msg', 'Unknown error')}")

        return result.get("data")

    async def async_send_text(self, text: str, target: str) -> SendResult:
        """Send a text message asynchronously.

        Args:
            text: Text content.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status and message ID.
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)
            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, target, text)

            message_segments = [{"type": "text", "data": {"text": text}}]

            if user_id:
                endpoint = "/send_private_msg"
                payload = {"user_id": user_id, "message": message_segments}
            else:
                endpoint = "/send_group_msg"
                payload = {"group_id": group_id, "message": message_segments}

            result = await self._async_call_api(endpoint, payload)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            return SendResult.ok(message_id, result)

        except Exception as e:
            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.FAILED, error=str(e))
            return SendResult.fail(str(e))

    async def async_send_image(self, image_key: str, target: str) -> SendResult:
        """Send an image message asynchronously.

        Args:
            image_key: Image URL or file path.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status and message ID.
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)
            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            message_segments = [{"type": "image", "data": {"file": image_key}}]

            if user_id:
                endpoint = "/send_private_msg"
                payload = {"user_id": user_id, "message": message_segments}
            else:
                endpoint = "/send_group_msg"
                payload = {"group_id": group_id, "message": message_segments}

            result = await self._async_call_api(endpoint, payload)
            return SendResult.ok(message_id, result)

        except Exception as e:
            return SendResult.fail(str(e))

    async def async_send_reply(
        self,
        reply_to_id: int,
        text: str,
        target: str,
    ) -> SendResult:
        """Send a reply message asynchronously.

        Args:
            reply_to_id: Message ID to reply to.
            text: Reply text.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status.
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)
            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            message_segments = [
                {"type": "reply", "data": {"id": str(reply_to_id)}},
                {"type": "text", "data": {"text": text}},
            ]

            if user_id:
                endpoint = "/send_private_msg"
                payload = {"user_id": user_id, "message": message_segments}
            else:
                endpoint = "/send_group_msg"
                payload = {"group_id": group_id, "message": message_segments}

            result = await self._async_call_api(endpoint, payload)
            return SendResult.ok(message_id, result)

        except Exception as e:
            return SendResult.fail(str(e))

    async def async_delete_msg(self, message_id: int) -> bool:
        """Delete a message asynchronously.

        Args:
            message_id: Message ID to delete.

        Returns:
            True if successful.
        """
        try:
            await self._async_call_api("/delete_msg", {"message_id": message_id})
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    async def async_get_group_info(self, group_id: int) -> dict[str, Any]:
        """Get group info asynchronously.

        Args:
            group_id: Group number.

        Returns:
            Group info dict.
        """
        try:
            return (
                await self._async_call_api(
                    "/get_group_info",
                    {"group_id": group_id},
                )
                or {}
            )
        except Exception as e:
            logger.error(f"Failed to get group info: {e}")
            return {}

    async def async_get_group_member_info(
        self,
        group_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """Get group member info asynchronously.

        Args:
            group_id: Group number.
            user_id: Member QQ number.

        Returns:
            Member info dict.
        """
        try:
            return (
                await self._async_call_api(
                    "/get_group_member_info",
                    {"group_id": group_id, "user_id": user_id},
                )
                or {}
            )
        except Exception as e:
            logger.error(f"Failed to get member info: {e}")
            return {}

    async def async_set_group_ban(
        self,
        group_id: int,
        user_id: int,
        duration: int = 1800,
    ) -> bool:
        """Ban a group member asynchronously.

        Args:
            group_id: Group number.
            user_id: Member to ban.
            duration: Ban duration in seconds (0 to unban).

        Returns:
            True if successful.
        """
        try:
            await self._async_call_api(
                "/set_group_ban",
                {"group_id": group_id, "user_id": user_id, "duration": duration},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to ban user: {e}")
            return False

    async def async_set_group_kick(
        self,
        group_id: int,
        user_id: int,
        reject_add_request: bool = False,
    ) -> bool:
        """Kick a group member asynchronously.

        Args:
            group_id: Group number.
            user_id: Member to kick.
            reject_add_request: Whether to reject future join requests.

        Returns:
            True if successful.
        """
        try:
            await self._async_call_api(
                "/set_group_kick",
                {
                    "group_id": group_id,
                    "user_id": user_id,
                    "reject_add_request": reject_add_request,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to kick user: {e}")
            return False

    async def async_send_poke(
        self,
        user_id: int,
        group_id: int | None = None,
    ) -> bool:
        """Send poke asynchronously.

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
            await self._async_call_api("/send_poke", payload)
            return True
        except Exception as e:
            logger.error(f"Failed to send poke: {e}")
            return False

    async def async_get_msg(self, message_id: int) -> dict[str, Any]:
        """Get message details asynchronously.

        Args:
            message_id: Message ID.

        Returns:
            Message info dict.
        """
        try:
            return (
                await self._async_call_api(
                    "/get_msg",
                    {"message_id": message_id},
                )
                or {}
            )
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return {}

    async def async_get_group_msg_history(
        self,
        group_id: int,
        message_seq: int = 0,
        count: int = 20,
    ) -> list[dict[str, Any]]:
        """Get group message history asynchronously.

        Args:
            group_id: Group number.
            message_seq: Starting message sequence.
            count: Number of messages.

        Returns:
            List of message dicts.
        """
        try:
            data = await self._async_call_api(
                "/get_group_msg_history",
                {"group_id": group_id, "message_seq": message_seq, "count": count},
            )
            return data.get("messages", []) if data else []
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []

    async def async_get_group_member_list(
        self,
        group_id: int,
    ) -> list[dict[str, Any]]:
        """Get all members of a group asynchronously.

        Args:
            group_id: Group number.

        Returns:
            List of member info dicts.
        """
        try:
            data = await self._async_call_api(
                "/get_group_member_list",
                {"group_id": group_id},
            )
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to get group member list: {e}")
            return []

    async def async_ocr_image(self, image: str) -> list[dict[str, Any]]:
        """Perform OCR on an image asynchronously.

        Args:
            image: Image URL or file path.

        Returns:
            List of OCR result dicts with text and coordinates.
        """
        try:
            data = await self._async_call_api("/ocr_image", {"image": image})
            if data:
                return data.get("texts", []) if isinstance(data, dict) else data
            return []
        except Exception as e:
            logger.error(f"Failed to OCR image: {e}")
            return []

    async def __aenter__(self) -> AsyncNapcatMixin:
        """Async context manager entry."""
        await self.async_connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.async_disconnect()
