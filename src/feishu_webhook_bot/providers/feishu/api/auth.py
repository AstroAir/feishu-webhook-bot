"""Authentication and token management for Feishu API.

This module handles:
- Tenant access token management
- App access token management
- OAuth authorization flow
- Token refresh
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from ....core.logger import get_logger
from .models import FeishuAPIError, TokenInfo, UserToken

if TYPE_CHECKING:
    import httpx

logger = get_logger("feishu_api.auth")


class FeishuAuthMixin:
    """Mixin providing authentication functionality for Feishu API.

    This mixin should be used with a class that has:
    - self.app_id: str
    - self.app_secret: str
    - self._client: httpx.AsyncClient
    - self._token_lock: asyncio.Lock
    - self._tenant_token: TokenInfo | None
    - self._app_token: TokenInfo | None
    - self._ensure_client() -> httpx.AsyncClient
    """

    # API endpoints
    TENANT_TOKEN_URL = "/auth/v3/tenant_access_token/internal"
    APP_TOKEN_URL = "/auth/v3/app_access_token/internal"
    USER_TOKEN_URL = "/authen/v1/oidc/access_token"
    REFRESH_TOKEN_URL = "/authen/v1/oidc/refresh_access_token"
    OAUTH_URL = "https://open.feishu.cn/open-apis/authen/v1/authorize"

    # These will be set by the main class
    app_id: str
    app_secret: str
    _client: httpx.AsyncClient | None
    _token_lock: asyncio.Lock
    _tenant_token: TokenInfo | None
    _app_token: TokenInfo | None

    def _ensure_client(self) -> Any:
        """Ensure HTTP client is initialized. To be implemented by main class."""
        raise NotImplementedError

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
