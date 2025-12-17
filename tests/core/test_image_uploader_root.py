"""Tests for Feishu Image Uploader module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.core.image_uploader import (
    PERMISSION_DENIED_CODE,
    FeishuImageUploader,
    FeishuImageUploaderError,
    FeishuPermissionChecker,
    FeishuPermissionDeniedError,
    PermissionError,
)


class TestFeishuPermissionChecker:
    """Test FeishuPermissionChecker class."""

    def test_get_auth_url(self):
        """Test generating authorization URL."""
        url = FeishuPermissionChecker.get_auth_url(
            "cli_test123", ["im:resource", "im:resource:upload"]
        )
        assert "cli_test123" in url
        assert "im:resource" in url
        assert "im:resource:upload" in url
        assert "open.feishu.cn" in url

    def test_get_app_config_url(self):
        """Test getting app configuration URL."""
        url = FeishuPermissionChecker.get_app_config_url("cli_test123")
        assert "cli_test123" in url
        assert "open.feishu.cn/app" in url

    def test_parse_permission_error_valid(self):
        """Test parsing a valid permission error response."""
        response_data = {
            "code": PERMISSION_DENIED_CODE,
            "msg": "Access denied",
            "error": {
                "permission_violations": [
                    {"type": "action_scope_required", "subject": "im:resource"},
                    {"type": "action_scope_required", "subject": "im:resource:upload"},
                ]
            },
        }

        result = FeishuPermissionChecker.parse_permission_error(response_data, "cli_test123")

        assert result is not None
        assert result.code == PERMISSION_DENIED_CODE
        assert "im:resource" in result.required_permissions
        assert "im:resource:upload" in result.required_permissions
        assert result.auth_url is not None
        assert "cli_test123" in result.auth_url

    def test_parse_permission_error_not_permission_error(self):
        """Test parsing a non-permission error response."""
        response_data = {
            "code": 10003,
            "msg": "Invalid app",
        }

        result = FeishuPermissionChecker.parse_permission_error(response_data, "cli_test123")

        assert result is None

    def test_parse_permission_error_no_violations(self):
        """Test parsing permission error without violation details."""
        response_data = {
            "code": PERMISSION_DENIED_CODE,
            "msg": "Access denied",
            "error": {},
        }

        result = FeishuPermissionChecker.parse_permission_error(response_data, "cli_test123")

        assert result is not None
        # Should use default permissions
        assert len(result.required_permissions) > 0

    def test_permissions_dict(self):
        """Test PERMISSIONS dictionary has expected entries."""
        assert "image_upload" in FeishuPermissionChecker.PERMISSIONS
        assert "file_upload" in FeishuPermissionChecker.PERMISSIONS
        assert "message_send" in FeishuPermissionChecker.PERMISSIONS


class TestPermissionErrorDataclass:
    """Test PermissionError dataclass."""

    def test_str_representation(self):
        """Test string representation of PermissionError."""
        error = PermissionError(
            code=PERMISSION_DENIED_CODE,
            message="Access denied",
            required_permissions=["im:resource", "im:resource:upload"],
            auth_url="https://example.com/auth",
        )

        str_repr = str(error)
        assert "im:resource" in str_repr
        assert "im:resource:upload" in str_repr
        assert "https://example.com/auth" in str_repr


class TestFeishuImageUploader:
    """Test FeishuImageUploader class."""

    @pytest.fixture
    def uploader(self):
        """Create an uploader instance for testing."""
        return FeishuImageUploader(
            app_id="cli_test123",
            app_secret="secret123",
            auto_open_auth=False,
        )

    def test_init(self, uploader):
        """Test uploader initialization."""
        assert uploader.app_id == "cli_test123"
        assert uploader.app_secret == "secret123"
        assert uploader.auto_open_auth is False
        assert uploader._token is None

    def test_init_with_auto_open(self):
        """Test uploader initialization with auto_open_auth."""
        uploader = FeishuImageUploader(
            app_id="cli_test",
            app_secret="secret",
            auto_open_auth=True,
        )
        assert uploader.auto_open_auth is True
        uploader.close()

    def test_context_manager(self):
        """Test uploader as context manager."""
        with FeishuImageUploader(
            app_id="cli_test",
            app_secret="secret",
        ) as uploader:
            assert uploader is not None

    def test_get_auth_url(self, uploader):
        """Test get_auth_url method."""
        url = uploader.get_auth_url()
        assert "cli_test123" in url
        assert "im:resource" in url

    def test_get_auth_url_custom_permissions(self, uploader):
        """Test get_auth_url with custom permissions."""
        url = uploader.get_auth_url(["custom:permission"])
        assert "custom:permission" in url

    @patch("feishu_webhook_bot.core.image_uploader.httpx.Client")
    def test_get_tenant_access_token_success(self, mock_client_class, uploader):
        """Test successful token retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token_123",
            "expire": 7200,
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        uploader._client = mock_client

        token = uploader._get_tenant_access_token()

        assert token == "test_token_123"
        assert uploader._token == "test_token_123"

    @patch("feishu_webhook_bot.core.image_uploader.httpx.Client")
    def test_get_tenant_access_token_cached(self, mock_client_class, uploader):
        """Test that token is cached."""
        uploader._token = "cached_token"

        token = uploader._get_tenant_access_token()

        assert token == "cached_token"

    @patch("feishu_webhook_bot.core.image_uploader.httpx.Client")
    def test_get_tenant_access_token_failure(self, mock_client_class, uploader):
        """Test token retrieval failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 10003,
            "msg": "Invalid app credentials",
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        uploader._client = mock_client

        with pytest.raises(ValueError, match="Failed to get token"):
            uploader._get_tenant_access_token()

    def test_handle_api_response_success(self, uploader):
        """Test handling successful API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"image_key": "img_xxx"},
        }

        result = uploader._handle_api_response(mock_response, "test operation")

        assert result["code"] == 0
        assert result["data"]["image_key"] == "img_xxx"

    def test_handle_api_response_permission_error(self, uploader):
        """Test handling permission denied error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": PERMISSION_DENIED_CODE,
            "msg": "Access denied",
            "error": {
                "permission_violations": [
                    {"type": "action_scope_required", "subject": "im:resource"},
                ]
            },
        }

        with pytest.raises(FeishuPermissionDeniedError) as exc_info:
            uploader._handle_api_response(mock_response, "test operation")

        assert "im:resource" in exc_info.value.required_permissions
        assert exc_info.value.auth_url is not None

    @patch.object(FeishuPermissionChecker, "open_auth_page")
    def test_handle_api_response_auto_open(self, mock_open_auth):
        """Test auto-opening browser on permission error."""
        uploader = FeishuImageUploader(
            app_id="cli_test",
            app_secret="secret",
            auto_open_auth=True,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": PERMISSION_DENIED_CODE,
            "msg": "Access denied",
            "error": {
                "permission_violations": [
                    {"type": "action_scope_required", "subject": "im:resource"},
                ]
            },
        }

        with pytest.raises(FeishuPermissionDeniedError):
            uploader._handle_api_response(mock_response, "test operation")

        mock_open_auth.assert_called_once()
        uploader.close()

    def test_handle_api_response_other_error(self, uploader):
        """Test handling other API errors."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 10003,
            "msg": "Invalid request",
        }

        with pytest.raises(FeishuImageUploaderError, match="Invalid request"):
            uploader._handle_api_response(mock_response, "test operation")


class TestFeishuPermissionDeniedError:
    """Test FeishuPermissionDeniedError exception."""

    def test_exception_attributes(self):
        """Test exception has expected attributes."""
        error = FeishuPermissionDeniedError(
            message="Access denied",
            required_permissions=["im:resource"],
            auth_url="https://example.com/auth",
        )

        assert str(error) == "Access denied"
        assert error.required_permissions == ["im:resource"]
        assert error.auth_url == "https://example.com/auth"
