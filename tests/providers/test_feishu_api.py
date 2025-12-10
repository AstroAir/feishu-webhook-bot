"""Tests for providers.feishu_api module."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from feishu_webhook_bot.providers.feishu_api import (
    FeishuAPIError,
    FeishuOpenAPI,
    MessageSendResult,
    TokenInfo,
    UserToken,
    create_feishu_api,
)


class TestTokenInfo:
    """Tests for TokenInfo dataclass."""

    def test_create_token_info(self) -> None:
        """Test creating token info."""
        token = TokenInfo(
            token="test_token",
            expires_at=time.time() + 7200,
            token_type="tenant",
        )

        assert token.token == "test_token"
        assert token.token_type == "tenant"

    def test_is_expired_false(self) -> None:
        """Test token is not expired."""
        token = TokenInfo(
            token="test_token",
            expires_at=time.time() + 7200,
            token_type="tenant",
        )

        assert token.is_expired() is False

    def test_is_expired_true(self) -> None:
        """Test token is expired."""
        token = TokenInfo(
            token="test_token",
            expires_at=time.time() - 100,
            token_type="tenant",
        )

        assert token.is_expired() is True

    def test_is_expired_with_buffer(self) -> None:
        """Test token expiration with buffer."""
        token = TokenInfo(
            token="test_token",
            expires_at=time.time() + 200,
            token_type="tenant",
        )

        assert token.is_expired(buffer_seconds=300) is True
        assert token.is_expired(buffer_seconds=100) is False


class TestUserToken:
    """Tests for UserToken dataclass."""

    def test_create_user_token(self) -> None:
        """Test creating user token."""
        token = UserToken(
            access_token="access_123",
            refresh_token="refresh_456",
            expires_in=7200,
            open_id="ou_xxx",
        )

        assert token.access_token == "access_123"
        assert token.refresh_token == "refresh_456"
        assert token.open_id == "ou_xxx"

    def test_is_expired_false(self) -> None:
        """Test user token is not expired."""
        token = UserToken(
            access_token="access_123",
            refresh_token="refresh_456",
            expires_in=7200,
        )

        assert token.is_expired() is False

    def test_is_expired_true(self) -> None:
        """Test user token is expired."""
        token = UserToken(
            access_token="access_123",
            refresh_token="refresh_456",
            expires_in=0,
            obtained_at=time.time() - 1000,
        )

        assert token.is_expired() is True


class TestMessageSendResult:
    """Tests for MessageSendResult dataclass."""

    def test_ok_result(self) -> None:
        """Test creating successful result."""
        result = MessageSendResult.ok("msg_123")

        assert result.success is True
        assert result.message_id == "msg_123"
        assert result.error_code == 0
        assert result.error_msg == ""

    def test_fail_result(self) -> None:
        """Test creating failed result."""
        result = MessageSendResult.fail(10001, "Invalid token")

        assert result.success is False
        assert result.message_id == ""
        assert result.error_code == 10001
        assert result.error_msg == "Invalid token"


class TestFeishuAPIError:
    """Tests for FeishuAPIError exception."""

    def test_create_error(self) -> None:
        """Test creating API error."""
        error = FeishuAPIError(10001, "Invalid token", "log_123")

        assert error.code == 10001
        assert error.msg == "Invalid token"
        assert error.log_id == "log_123"
        assert "10001" in str(error)
        assert "Invalid token" in str(error)


class TestFeishuOpenAPI:
    """Tests for FeishuOpenAPI client."""

    def test_init(self) -> None:
        """Test client initialization."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
            timeout=30.0,
        )

        assert api.app_id == "cli_xxx"
        assert api.app_secret == "secret_xxx"
        assert api.timeout == 30.0
        assert api._client is None

    def test_init_with_custom_base_url(self) -> None:
        """Test client with custom base URL."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
            base_url="https://custom.api.com",
        )

        assert api.base_url == "https://custom.api.com"

    @pytest.mark.anyio
    async def test_connect_and_close(self) -> None:
        """Test connecting and closing client."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        await api.connect()
        assert api._client is not None

        await api.close()
        assert api._client is None

    @pytest.mark.anyio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        async with FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        ) as api:
            assert api._client is not None

    def test_ensure_client_raises_when_not_connected(self) -> None:
        """Test _ensure_client raises when not connected."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        with pytest.raises(RuntimeError, match="not connected"):
            api._ensure_client()

    def test_get_oauth_url(self) -> None:
        """Test generating OAuth URL."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        url = api.get_oauth_url(
            redirect_uri="https://example.com/callback",
            state="random_state",
        )

        assert "cli_xxx" in url
        assert "example.com" in url
        assert "random_state" in url

    def test_get_oauth_url_with_scope(self) -> None:
        """Test generating OAuth URL with scope."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        url = api.get_oauth_url(
            redirect_uri="https://example.com/callback",
            state="state",
            scope="contact:user.base:readonly",
        )

        assert "scope" in url

    @pytest.mark.anyio
    async def test_get_tenant_access_token(self) -> None:
        """Test getting tenant access token."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "t-xxx",
            "expire": 7200,
        }
        mock_client.post.return_value = mock_response
        api._client = mock_client

        token = await api.get_tenant_access_token()

        assert token == "t-xxx"
        assert api._tenant_token is not None
        assert api._tenant_token.token == "t-xxx"

    @pytest.mark.anyio
    async def test_get_tenant_access_token_cached(self) -> None:
        """Test cached tenant access token is returned."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        api._tenant_token = TokenInfo(
            token="cached_token",
            expires_at=time.time() + 7200,
            token_type="tenant",
        )
        api._client = AsyncMock()

        token = await api.get_tenant_access_token()

        assert token == "cached_token"
        api._client.post.assert_not_called()

    @pytest.mark.anyio
    async def test_get_tenant_access_token_error(self) -> None:
        """Test error handling for tenant token request."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 10001,
            "msg": "Invalid app_id",
        }
        mock_client.post.return_value = mock_response
        api._client = mock_client

        with pytest.raises(FeishuAPIError) as exc_info:
            await api.get_tenant_access_token()

        assert exc_info.value.code == 10001

    @pytest.mark.anyio
    async def test_send_message(self) -> None:
        """Test sending message."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        api._tenant_token = TokenInfo(
            token="t-xxx",
            expires_at=time.time() + 7200,
            token_type="tenant",
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "om_xxx"},
        }
        mock_client.post.return_value = mock_response
        api._client = mock_client

        result = await api.send_message(
            receive_id="ou_xxx",
            receive_id_type="open_id",
            msg_type="text",
            content={"text": "Hello"},
        )

        assert result.success is True
        assert result.message_id == "om_xxx"

    @pytest.mark.anyio
    async def test_send_message_error(self) -> None:
        """Test send message error handling."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        api._tenant_token = TokenInfo(
            token="t-xxx",
            expires_at=time.time() + 7200,
            token_type="tenant",
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 99991,
            "msg": "Rate limited",
        }
        mock_client.post.return_value = mock_response
        api._client = mock_client

        result = await api.send_message(
            receive_id="ou_xxx",
            receive_id_type="open_id",
            msg_type="text",
            content={"text": "Hello"},
        )

        assert result.success is False
        assert result.error_code == 99991

    @pytest.mark.anyio
    async def test_reply_message(self) -> None:
        """Test replying to message."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        api._tenant_token = TokenInfo(
            token="t-xxx",
            expires_at=time.time() + 7200,
            token_type="tenant",
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "om_reply"},
        }
        mock_client.post.return_value = mock_response
        api._client = mock_client

        result = await api.reply_message(
            message_id="om_original",
            msg_type="text",
            content={"text": "Reply"},
        )

        assert result.success is True
        assert result.message_id == "om_reply"

    @pytest.mark.anyio
    async def test_send_text(self) -> None:
        """Test send_text convenience method."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        api._tenant_token = TokenInfo(
            token="t-xxx",
            expires_at=time.time() + 7200,
            token_type="tenant",
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "om_xxx"},
        }
        mock_client.post.return_value = mock_response
        api._client = mock_client

        result = await api.send_text("oc_xxx", "Hello!")

        assert result.success is True

    @pytest.mark.anyio
    async def test_reply_text(self) -> None:
        """Test reply_text convenience method."""
        api = FeishuOpenAPI(
            app_id="cli_xxx",
            app_secret="secret_xxx",
        )

        api._tenant_token = TokenInfo(
            token="t-xxx",
            expires_at=time.time() + 7200,
            token_type="tenant",
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "om_reply"},
        }
        mock_client.post.return_value = mock_response
        api._client = mock_client

        result = await api.reply_text("om_original", "Reply!")

        assert result.success is True


class TestCreateFeishuApi:
    """Tests for create_feishu_api factory function."""

    def test_create_feishu_api(self) -> None:
        """Test factory function."""
        api = create_feishu_api(
            app_id="cli_xxx",
            app_secret="secret_xxx",
            timeout=60.0,
        )

        assert isinstance(api, FeishuOpenAPI)
        assert api.app_id == "cli_xxx"
        assert api.timeout == 60.0
