"""Feishu Open Platform API client.

This module provides the main FeishuOpenAPI client class that combines
all API functionality through mixins.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ....core.logger import get_logger
from .auth import FeishuAuthMixin
from .chat import FeishuChatMixin
from .media import FeishuMediaMixin
from .message import FeishuMessageMixin
from .models import TokenInfo
from .user import FeishuUserMixin

logger = get_logger("feishu_api")


class FeishuOpenAPI(
    FeishuAuthMixin,
    FeishuMessageMixin,
    FeishuUserMixin,
    FeishuChatMixin,
    FeishuMediaMixin,
):
    """Feishu Open Platform API client.

    Provides comprehensive access to Feishu Open Platform APIs including:
    - Token management with automatic refresh
    - Message sending and replying
    - User and chat information queries
    - OAuth authorization flow
    - File/media operations
    - Chat management

    The client handles token management automatically, refreshing tokens
    before they expire.

    Example:
        ```python
        async with FeishuOpenAPI(app_id="xxx", app_secret="xxx") as api:
            # Send a text message
            result = await api.send_message(
                receive_id="ou_xxx",
                receive_id_type="open_id",
                msg_type="text",
                content={"text": "Hello!"},
            )

            if result.success:
                print(f"Sent message: {result.message_id}")

            # Get user info
            user = await api.get_user_info("ou_xxx")
            print(f"User: {user.get('name')}")
        ```
    """

    # API base URL
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        timeout: float = 30.0,
        base_url: str | None = None,
    ):
        """Initialize Feishu API client.

        Args:
            app_id: Feishu application ID.
            app_secret: Feishu application secret.
            timeout: HTTP request timeout in seconds.
            base_url: Override base URL (for testing or regional endpoints).
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout = timeout
        self.base_url = base_url or self.BASE_URL

        self._client: httpx.AsyncClient | None = None
        self._tenant_token: TokenInfo | None = None
        self._app_token: TokenInfo | None = None
        self._token_lock = asyncio.Lock()

    async def __aenter__(self) -> FeishuOpenAPI:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                base_url=self.base_url,
            )
            logger.debug("FeishuOpenAPI client connected")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("FeishuOpenAPI client closed")

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            raise RuntimeError(
                "FeishuOpenAPI client not connected. Use 'async with' or call connect() first."
            )
        return self._client


def create_feishu_api(
    app_id: str,
    app_secret: str,
    timeout: float = 30.0,
) -> FeishuOpenAPI:
    """Factory function to create Feishu API client.

    Args:
        app_id: Feishu application ID.
        app_secret: Feishu application secret.
        timeout: HTTP timeout.

    Returns:
        Configured FeishuOpenAPI instance.
    """
    return FeishuOpenAPI(
        app_id=app_id,
        app_secret=app_secret,
        timeout=timeout,
    )
