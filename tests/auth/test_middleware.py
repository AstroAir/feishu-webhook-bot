"""Comprehensive tests for authentication middleware module.

Tests cover:
- get_current_user_from_token function
- require_auth decorator
- get_current_nicegui_user function
- logout_user function
- AuthMiddleware class
- setup_auth_middleware function
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# Mock nicegui before importing middleware
sys.modules["nicegui"] = MagicMock()

from feishu_webhook_bot.auth.middleware import (
    AuthMiddleware,
    get_current_nicegui_user,
    get_current_user_from_token,
    logout_user,
    require_auth,
    setup_auth_middleware,
)


# ==============================================================================
# get_current_user_from_token Tests
# ==============================================================================


class TestGetCurrentUserFromToken:
    """Tests for get_current_user_from_token function."""

    def test_valid_token_returns_user(self):
        """Test valid token returns user data."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.to_dict.return_value = {"id": 1, "email": "test@example.com"}

        mock_auth_service = MagicMock()
        mock_auth_service.get_user_by_email.return_value = mock_user

        with patch(
            "feishu_webhook_bot.auth.middleware.decode_access_token"
        ) as mock_decode:
            mock_decode.return_value = {"sub": "test@example.com"}

            result = get_current_user_from_token(mock_credentials, mock_auth_service)

            assert result == {"id": 1, "email": "test@example.com"}

    def test_invalid_token_raises_401(self):
        """Test invalid token raises HTTPException."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"

        mock_auth_service = MagicMock()

        with patch(
            "feishu_webhook_bot.auth.middleware.decode_access_token"
        ) as mock_decode:
            mock_decode.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                get_current_user_from_token(mock_credentials, mock_auth_service)

            assert exc_info.value.status_code == 401
            assert "Invalid or expired token" in exc_info.value.detail

    def test_missing_sub_in_payload_raises_401(self):
        """Test missing 'sub' in payload raises HTTPException."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "token_without_sub"

        mock_auth_service = MagicMock()

        with patch(
            "feishu_webhook_bot.auth.middleware.decode_access_token"
        ) as mock_decode:
            mock_decode.return_value = {"other": "data"}

            with pytest.raises(HTTPException) as exc_info:
                get_current_user_from_token(mock_credentials, mock_auth_service)

            assert exc_info.value.status_code == 401
            assert "Invalid token payload" in exc_info.value.detail

    def test_user_not_found_raises_401(self):
        """Test user not found raises HTTPException."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        mock_auth_service = MagicMock()
        mock_auth_service.get_user_by_email.return_value = None

        with patch(
            "feishu_webhook_bot.auth.middleware.decode_access_token"
        ) as mock_decode:
            mock_decode.return_value = {"sub": "nonexistent@example.com"}

            with pytest.raises(HTTPException) as exc_info:
                get_current_user_from_token(mock_credentials, mock_auth_service)

            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail

    def test_inactive_user_raises_403(self):
        """Test inactive user raises HTTPException."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        mock_user = MagicMock()
        mock_user.is_active = False

        mock_auth_service = MagicMock()
        mock_auth_service.get_user_by_email.return_value = mock_user

        with patch(
            "feishu_webhook_bot.auth.middleware.decode_access_token"
        ) as mock_decode:
            mock_decode.return_value = {"sub": "inactive@example.com"}

            with pytest.raises(HTTPException) as exc_info:
                get_current_user_from_token(mock_credentials, mock_auth_service)

            assert exc_info.value.status_code == 403
            assert "inactive" in exc_info.value.detail


# ==============================================================================
# require_auth Decorator Tests
# ==============================================================================


class TestRequireAuth:
    """Tests for require_auth decorator."""

    def test_authenticated_user_allowed(self):
        """Test authenticated user can access protected page."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            mock_app.storage.user = {"authenticated": True, "token": "valid_token"}

            with patch(
                "feishu_webhook_bot.auth.middleware.decode_access_token"
            ) as mock_decode:
                mock_decode.return_value = {"sub": "test@example.com"}

                @require_auth
                def protected_page():
                    return "success"

                result = protected_page()
                assert result == "success"

    def test_unauthenticated_user_redirected(self):
        """Test unauthenticated user is redirected to login."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            mock_app.storage.user = {"authenticated": False}

            with patch("feishu_webhook_bot.auth.middleware.ui") as mock_ui:
                @require_auth
                def protected_page():
                    return "success"

                result = protected_page()

                assert result is None
                mock_ui.navigate.to.assert_called_with("/login")

    def test_expired_token_redirected(self):
        """Test expired token redirects to login."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            mock_app.storage.user = {"authenticated": True, "token": "expired_token"}

            with patch(
                "feishu_webhook_bot.auth.middleware.decode_access_token"
            ) as mock_decode:
                mock_decode.return_value = None

                with patch("feishu_webhook_bot.auth.middleware.ui") as mock_ui:
                    @require_auth
                    def protected_page():
                        return "success"

                    result = protected_page()

                    assert result is None
                    mock_ui.navigate.to.assert_called_with("/login")

    def test_no_storage_user_redirected(self):
        """Test missing storage.user redirects to login."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            # Remove user attribute
            del mock_app.storage.user

            with patch("feishu_webhook_bot.auth.middleware.ui") as mock_ui:
                @require_auth
                def protected_page():
                    return "success"

                result = protected_page()

                assert result is None
                mock_ui.navigate.to.assert_called_with("/login")


# ==============================================================================
# get_current_nicegui_user Tests
# ==============================================================================


class TestGetCurrentNiceguiUser:
    """Tests for get_current_nicegui_user function."""

    def test_authenticated_user_returns_data(self):
        """Test authenticated user returns user data."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            mock_app.storage.user = {
                "authenticated": True,
                "user_data": {"id": 1, "email": "test@example.com"},
            }

            result = get_current_nicegui_user()

            assert result == {"id": 1, "email": "test@example.com"}

    def test_unauthenticated_returns_none(self):
        """Test unauthenticated user returns None."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            mock_app.storage.user = {"authenticated": False, "user_data": None}

            result = get_current_nicegui_user()

            assert result is None

    def test_no_storage_returns_none(self):
        """Test missing storage returns None."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            del mock_app.storage.user

            result = get_current_nicegui_user()

            assert result is None


# ==============================================================================
# logout_user Tests
# ==============================================================================


class TestLogoutUser:
    """Tests for logout_user function."""

    def test_logout_clears_session(self):
        """Test logout clears user session."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            mock_app.storage.user = {
                "authenticated": True,
                "user_data": {"id": 1},
                "token": "some_token",
            }

            logout_user()

            assert mock_app.storage.user["authenticated"] is False
            assert mock_app.storage.user["user_data"] is None
            assert mock_app.storage.user["token"] is None

    def test_logout_no_storage_no_error(self):
        """Test logout with no storage doesn't raise error."""
        with patch("feishu_webhook_bot.auth.middleware.app") as mock_app:
            del mock_app.storage.user

            # Should not raise
            logout_user()


# ==============================================================================
# AuthMiddleware Tests
# ==============================================================================


class TestAuthMiddleware:
    """Tests for AuthMiddleware class."""

    @pytest.mark.anyio
    async def test_public_path_allowed(self):
        """Test public paths are allowed without authentication."""
        mock_app = MagicMock()
        middleware = AuthMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/auth/login"
        mock_request.headers.get.return_value = None

        mock_call_next = AsyncMock(return_value="response")

        result = await middleware(mock_request, mock_call_next)

        assert result == "response"
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.anyio
    async def test_protected_path_with_valid_token(self):
        """Test protected path with valid token adds user to request."""
        mock_app = MagicMock()
        middleware = AuthMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/protected"
        mock_request.headers.get.return_value = "Bearer valid_token"

        mock_call_next = AsyncMock(return_value="response")

        with patch(
            "feishu_webhook_bot.auth.middleware.decode_access_token"
        ) as mock_decode:
            mock_decode.return_value = {"sub": "test@example.com"}

            result = await middleware(mock_request, mock_call_next)

            assert result == "response"
            assert mock_request.state.user == {"sub": "test@example.com"}

    @pytest.mark.anyio
    async def test_protected_path_with_invalid_token(self):
        """Test protected path with invalid token continues without user."""
        mock_app = MagicMock()
        middleware = AuthMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/protected"
        mock_request.headers.get.return_value = "Bearer invalid_token"

        mock_call_next = AsyncMock(return_value="response")

        with patch(
            "feishu_webhook_bot.auth.middleware.decode_access_token"
        ) as mock_decode:
            mock_decode.return_value = None

            result = await middleware(mock_request, mock_call_next)

            assert result == "response"

    @pytest.mark.anyio
    async def test_protected_path_without_token(self):
        """Test protected path without token continues."""
        mock_app = MagicMock()
        middleware = AuthMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/protected"
        mock_request.headers.get.return_value = None

        mock_call_next = AsyncMock(return_value="response")

        result = await middleware(mock_request, mock_call_next)

        assert result == "response"

    @pytest.mark.anyio
    async def test_various_public_paths(self):
        """Test various public paths are allowed."""
        mock_app = MagicMock()
        middleware = AuthMiddleware(mock_app)

        public_paths = [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/health",
            "/api/auth/check-password-strength",
            "/login",
            "/register",
            "/healthz",
        ]

        for path in public_paths:
            mock_request = MagicMock()
            mock_request.url.path = path
            mock_request.headers.get.return_value = None

            mock_call_next = AsyncMock(return_value="response")

            result = await middleware(mock_request, mock_call_next)
            assert result == "response", f"Path {path} should be public"


# ==============================================================================
# setup_auth_middleware Tests
# ==============================================================================


class TestSetupAuthMiddleware:
    """Tests for setup_auth_middleware function."""

    def test_setup_registers_middleware(self):
        """Test setup_auth_middleware registers middleware on app."""
        mock_app = MagicMock()

        setup_auth_middleware(mock_app)

        mock_app.middleware.assert_called_once_with("http")
