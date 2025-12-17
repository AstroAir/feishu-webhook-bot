"""Feishu Open Platform API client for full bot functionality.

This module provides a comprehensive client for Feishu Open Platform APIs,
enabling full bot capabilities beyond simple webhooks:
- Token management (tenant_access_token, app_access_token)
- Message API (send, reply, recall messages)
- User/Chat info queries
- OAuth authorization flow (optional)

Example:
    ```python
    # Basic usage with tenant access token
    api = FeishuOpenAPI(
        app_id="cli_xxx",
        app_secret="xxx",
    )

    # Send message to a chat
    await api.send_message(
        receive_id="oc_xxx",
        receive_id_type="chat_id",
        msg_type="text",
        content={"text": "Hello!"},
    )

    # Reply to a message
    await api.reply_message(
        message_id="om_xxx",
        msg_type="text",
        content={"text": "This is a reply"},
    )
    ```
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from ..core.logger import get_logger

logger = get_logger("feishu_api")


# Token types
TokenType = Literal["tenant", "app", "user"]

# Receive ID types for message sending
ReceiveIdType = Literal["open_id", "user_id", "union_id", "email", "chat_id"]


@dataclass
class TokenInfo:
    """Access token information with expiration tracking.

    Attributes:
        token: The access token string.
        expires_at: Unix timestamp when token expires.
        token_type: Type of token (tenant, app, user).
    """

    token: str
    expires_at: float
    token_type: TokenType

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired or about to expire.

        Args:
            buffer_seconds: Consider expired if within this many seconds of expiry.

        Returns:
            True if token is expired or will expire soon.
        """
        return time.time() >= (self.expires_at - buffer_seconds)


@dataclass
class UserToken:
    """User access token from OAuth flow.

    Attributes:
        access_token: User access token for API calls.
        refresh_token: Token for refreshing access token.
        token_type: Usually "Bearer".
        expires_in: Token lifetime in seconds.
        scope: Authorized scopes.
        open_id: User's open_id.
        union_id: User's union_id.
        user_id: User's user_id (if available).
    """

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 7200
    scope: str = ""
    open_id: str = ""
    union_id: str = ""
    user_id: str = ""

    # Internal tracking
    obtained_at: float = field(default_factory=time.time)

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if user token is expired."""
        return time.time() >= (self.obtained_at + self.expires_in - buffer_seconds)


@dataclass
class MessageSendResult:
    """Result of message send operation.

    Attributes:
        success: Whether send succeeded.
        message_id: ID of sent message (if successful).
        error_code: Error code (if failed).
        error_msg: Error message (if failed).
    """

    success: bool
    message_id: str = ""
    error_code: int = 0
    error_msg: str = ""

    @classmethod
    def ok(cls, message_id: str) -> MessageSendResult:
        """Create successful result."""
        return cls(success=True, message_id=message_id)

    @classmethod
    def fail(cls, code: int, msg: str) -> MessageSendResult:
        """Create failed result."""
        return cls(success=False, error_code=code, error_msg=msg)


class FeishuAPIError(Exception):
    """Exception for Feishu API errors.

    Attributes:
        code: Feishu error code.
        msg: Error message.
        log_id: Request log ID for debugging.
    """

    def __init__(self, code: int, msg: str, log_id: str = ""):
        self.code = code
        self.msg = msg
        self.log_id = log_id
        super().__init__(f"Feishu API Error {code}: {msg} (log_id: {log_id})")


class FeishuOpenAPI:
    """Feishu Open Platform API client.

    Provides comprehensive access to Feishu Open Platform APIs including:
    - Token management with automatic refresh
    - Message sending and replying
    - User and chat information queries
    - OAuth authorization flow

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

    # API base URLs
    BASE_URL = "https://open.feishu.cn/open-apis"

    # Endpoints
    TENANT_TOKEN_URL = "/auth/v3/tenant_access_token/internal"
    APP_TOKEN_URL = "/auth/v3/app_access_token/internal"
    USER_TOKEN_URL = "/authen/v1/oidc/access_token"
    REFRESH_TOKEN_URL = "/authen/v1/oidc/refresh_access_token"

    SEND_MESSAGE_URL = "/im/v1/messages"
    REPLY_MESSAGE_URL = "/im/v1/messages/{message_id}/reply"
    GET_MESSAGE_URL = "/im/v1/messages/{message_id}"
    RECALL_MESSAGE_URL = "/im/v1/messages/{message_id}"

    GET_USER_URL = "/contact/v3/users/{user_id}"
    GET_CHAT_URL = "/im/v1/chats/{chat_id}"
    GET_CHAT_MEMBERS_URL = "/im/v1/chats/{chat_id}/members"

    OAUTH_URL = "https://open.feishu.cn/open-apis/authen/v1/authorize"

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

    # =========================================================================
    # Token Management
    # =========================================================================

    async def get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """Get tenant access token, refreshing if needed.

        Args:
            force_refresh: Force token refresh even if not expired.

        Returns:
            Valid tenant access token.

        Raises:
            FeishuAPIError: If token request fails.
        """
        async with self._token_lock:
            if not force_refresh and self._tenant_token and not self._tenant_token.is_expired():
                return self._tenant_token.token

            logger.debug("Requesting new tenant_access_token")

            client = self._ensure_client()
            response = await client.post(
                self.TENANT_TOKEN_URL,
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret,
                },
            )

            data = response.json()
            if data.get("code") != 0:
                raise FeishuAPIError(
                    code=data.get("code", -1),
                    msg=data.get("msg", "Unknown error"),
                )

            token = data["tenant_access_token"]
            expire = data.get("expire", 7200)

            self._tenant_token = TokenInfo(
                token=token,
                expires_at=time.time() + expire,
                token_type="tenant",
            )

            logger.info("Obtained tenant_access_token (expires in %d seconds)", expire)
            return token

    async def get_app_access_token(self, force_refresh: bool = False) -> str:
        """Get app access token, refreshing if needed.

        Args:
            force_refresh: Force token refresh even if not expired.

        Returns:
            Valid app access token.

        Raises:
            FeishuAPIError: If token request fails.
        """
        async with self._token_lock:
            if not force_refresh and self._app_token and not self._app_token.is_expired():
                return self._app_token.token

            logger.debug("Requesting new app_access_token")

            client = self._ensure_client()
            response = await client.post(
                self.APP_TOKEN_URL,
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret,
                },
            )

            data = response.json()
            if data.get("code") != 0:
                raise FeishuAPIError(
                    code=data.get("code", -1),
                    msg=data.get("msg", "Unknown error"),
                )

            token = data["app_access_token"]
            expire = data.get("expire", 7200)

            self._app_token = TokenInfo(
                token=token,
                expires_at=time.time() + expire,
                token_type="app",
            )

            logger.info("Obtained app_access_token (expires in %d seconds)", expire)
            return token

    # =========================================================================
    # OAuth Flow
    # =========================================================================

    def get_oauth_url(
        self,
        redirect_uri: str,
        state: str = "",
        scope: str = "",
    ) -> str:
        """Generate OAuth authorization URL.

        Args:
            redirect_uri: Callback URL after authorization.
            state: State parameter for CSRF protection.
            scope: Space-separated list of scopes (optional).

        Returns:
            OAuth authorization URL to redirect user to.

        Example:
            ```python
            url = api.get_oauth_url(
                redirect_uri="https://example.com/callback",
                state="random_state_string",
            )
            # Redirect user to this URL
            ```
        """
        from urllib.parse import urlencode

        params = {
            "app_id": self.app_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        if scope:
            params["scope"] = scope

        return f"{self.OAUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> UserToken:
        """Exchange authorization code for user access token.

        Args:
            code: Authorization code from OAuth callback.

        Returns:
            UserToken with access and refresh tokens.

        Raises:
            FeishuAPIError: If token exchange fails.
        """
        client = self._ensure_client()
        app_token = await self.get_app_access_token()

        response = await client.post(
            self.USER_TOKEN_URL,
            headers={"Authorization": f"Bearer {app_token}"},
            json={
                "grant_type": "authorization_code",
                "code": code,
            },
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        token_data = data.get("data", {})
        return UserToken(
            access_token=token_data.get("access_token", ""),
            refresh_token=token_data.get("refresh_token", ""),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 7200),
            scope=token_data.get("scope", ""),
            open_id=token_data.get("open_id", ""),
            union_id=token_data.get("union_id", ""),
            user_id=token_data.get("user_id", ""),
        )

    async def refresh_user_token(self, refresh_token: str) -> UserToken:
        """Refresh user access token.

        Args:
            refresh_token: Refresh token from previous authorization.

        Returns:
            New UserToken with updated tokens.

        Raises:
            FeishuAPIError: If token refresh fails.
        """
        client = self._ensure_client()
        app_token = await self.get_app_access_token()

        response = await client.post(
            self.REFRESH_TOKEN_URL,
            headers={"Authorization": f"Bearer {app_token}"},
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        token_data = data.get("data", {})
        return UserToken(
            access_token=token_data.get("access_token", ""),
            refresh_token=token_data.get("refresh_token", ""),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 7200),
            scope=token_data.get("scope", ""),
            open_id=token_data.get("open_id", ""),
            union_id=token_data.get("union_id", ""),
            user_id=token_data.get("user_id", ""),
        )

    # =========================================================================
    # Message API
    # =========================================================================

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

    # =========================================================================
    # User & Chat API
    # =========================================================================

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
        params = {"page_size": page_size}
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

    # =========================================================================
    # Convenience Methods
    # =========================================================================

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
