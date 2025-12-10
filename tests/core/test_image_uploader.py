"""Comprehensive tests for image uploader functionality.

Tests cover:
- FeishuPermissionChecker utilities
- FeishuImageUploader initialization
- Token management
- Image upload operations
- Permission error handling
- Helper functions
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from feishu_webhook_bot.core.image_uploader import (
    FeishuImageUploader,
    FeishuPermissionChecker,
    FeishuPermissionDeniedError,
    PermissionError as FeishuPermissionError,
    create_image_card,
)


# ==============================================================================
# FeishuPermissionChecker Tests
# ==============================================================================


class TestFeishuPermissionChecker:
    """Tests for FeishuPermissionChecker utility class."""

    def test_get_auth_url(self):
        """Test generating authorization URL."""
        url = FeishuPermissionChecker.get_auth_url(
            app_id="cli_test123",
            permissions=["im:resource", "im:resource:upload"],
        )

        assert "cli_test123" in url
        assert "im:resource" in url
        assert "open.feishu.cn" in url

    def test_get_app_config_url(self):
        """Test getting app configuration URL."""
        url = FeishuPermissionChecker.get_app_config_url("cli_test123")

        assert "cli_test123" in url
        assert "open.feishu.cn" in url
        assert "auth" in url

    def test_parse_permission_error_not_permission_error(self):
        """Test parse_permission_error returns None for non-permission errors."""
        response_data = {"code": 99991663, "msg": "Invalid token"}

        result = FeishuPermissionChecker.parse_permission_error(
            response_data, "cli_test"
        )

        assert result is None

    def test_parse_permission_error_permission_denied(self):
        """Test parse_permission_error parses permission denied error."""
        response_data = {
            "code": 99991672,
            "msg": "Permission denied",
            "error": {
                "permission_violations": [
                    {"type": "action_scope_required", "subject": "im:resource"},
                ]
            },
        }

        result = FeishuPermissionChecker.parse_permission_error(
            response_data, "cli_test"
        )

        assert result is not None
        assert result.code == 99991672
        assert "im:resource" in result.required_permissions
        assert result.auth_url is not None

    def test_parse_permission_error_default_permissions(self):
        """Test parse_permission_error uses defaults when no violations."""
        response_data = {
            "code": 99991672,
            "msg": "Permission denied",
            "error": {},
        }

        result = FeishuPermissionChecker.parse_permission_error(
            response_data, "cli_test"
        )

        assert result is not None
        assert len(result.required_permissions) > 0

    @patch("webbrowser.open")
    def test_open_auth_page_success(self, mock_webbrowser):
        """Test opening auth page in browser."""
        mock_webbrowser.return_value = True

        result = FeishuPermissionChecker.open_auth_page("https://example.com/auth")

        assert result is True
        mock_webbrowser.assert_called_once()

    @patch("subprocess.run")
    @patch("webbrowser.open")
    def test_open_auth_page_failure(self, mock_webbrowser, mock_subprocess):
        """Test handling browser open failure."""
        mock_webbrowser.side_effect = Exception("Browser error")
        mock_subprocess.side_effect = Exception("Subprocess error")

        # Should not raise, returns False
        result = FeishuPermissionChecker.open_auth_page(
            "https://example.com/auth", silent=True
        )

        assert result is False


class TestPermissionErrorDataclass:
    """Tests for PermissionError dataclass."""

    def test_permission_error_str(self):
        """Test PermissionError string representation."""
        error = FeishuPermissionError(
            code=99991672,
            message="Permission denied",
            required_permissions=["im:resource"],
            auth_url="https://example.com/auth",
        )

        str_repr = str(error)

        assert "im:resource" in str_repr
        assert "https://example.com/auth" in str_repr


# ==============================================================================
# FeishuImageUploader Initialization Tests
# ==============================================================================


class TestFeishuImageUploaderInitialization:
    """Tests for FeishuImageUploader initialization."""

    def test_uploader_creation(self):
        """Test basic uploader creation."""
        uploader = FeishuImageUploader(
            app_id="cli_test",
            app_secret="secret123",
        )

        assert uploader.app_id == "cli_test"
        assert uploader.app_secret == "secret123"
        assert uploader.timeout == 30.0
        assert uploader.auto_open_auth is False

    def test_uploader_custom_settings(self):
        """Test uploader with custom settings."""
        uploader = FeishuImageUploader(
            app_id="cli_test",
            app_secret="secret",
            timeout=60.0,
            auto_open_auth=True,
        )

        assert uploader.timeout == 60.0
        assert uploader.auto_open_auth is True

    def test_uploader_context_manager(self):
        """Test uploader as context manager."""
        with FeishuImageUploader("cli_test", "secret") as uploader:
            assert uploader is not None

    def test_uploader_close(self):
        """Test uploader close method."""
        uploader = FeishuImageUploader("cli_test", "secret")
        # Should not raise
        uploader.close()


# ==============================================================================
# Token Management Tests
# ==============================================================================


class TestTokenManagement:
    """Tests for token management."""

    @patch("httpx.Client.post")
    def test_get_tenant_access_token_success(self, mock_post):
        """Test successful token retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token_123",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        uploader = FeishuImageUploader("cli_test", "secret")
        token = uploader._get_tenant_access_token()

        assert token == "test_token_123"
        mock_post.assert_called_once()

    @patch("httpx.Client.post")
    def test_get_tenant_access_token_cached(self, mock_post):
        """Test token is cached."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "cached_token",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        uploader = FeishuImageUploader("cli_test", "secret")

        # First call
        token1 = uploader._get_tenant_access_token()
        # Second call should use cache
        token2 = uploader._get_tenant_access_token()

        assert token1 == token2
        assert mock_post.call_count == 1

    @patch("httpx.Client.post")
    def test_get_tenant_access_token_force_refresh(self, mock_post):
        """Test force refresh bypasses cache."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "new_token",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        uploader = FeishuImageUploader("cli_test", "secret")
        uploader._token = "old_token"

        token = uploader._get_tenant_access_token(force_refresh=True)

        assert token == "new_token"
        mock_post.assert_called_once()

    @patch("httpx.Client.post")
    def test_get_tenant_access_token_failure(self, mock_post):
        """Test token retrieval failure."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 10003,
            "msg": "Invalid app credentials",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        uploader = FeishuImageUploader("cli_test", "wrong_secret")

        with pytest.raises(ValueError, match="Invalid app"):
            uploader._get_tenant_access_token()


# ==============================================================================
# Image Upload Tests
# ==============================================================================


class TestImageUpload:
    """Tests for image upload operations."""

    @patch("httpx.Client.post")
    def test_upload_image_success(self, mock_post):
        """Test successful image upload."""
        # Mock token response
        token_response = Mock()
        token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        token_response.raise_for_status = Mock()

        # Mock upload response
        upload_response = Mock()
        upload_response.json.return_value = {
            "code": 0,
            "data": {"image_key": "img_v2_test123"},
        }
        upload_response.raise_for_status = Mock()

        mock_post.side_effect = [token_response, upload_response]

        # Create a temporary test image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write minimal PNG data
            f.write(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            ))
            temp_path = f.name

        try:
            uploader = FeishuImageUploader("cli_test", "secret")
            image_key = uploader.upload_image(temp_path)

            assert image_key == "img_v2_test123"
        finally:
            Path(temp_path).unlink()

    def test_upload_image_file_not_found(self):
        """Test upload with nonexistent file."""
        uploader = FeishuImageUploader("cli_test", "secret")

        with pytest.raises(FileNotFoundError):
            uploader.upload_image("/nonexistent/path/image.png")

    @patch("httpx.Client.post")
    def test_upload_image_bytes_success(self, mock_post):
        """Test uploading image bytes."""
        token_response = Mock()
        token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        token_response.raise_for_status = Mock()

        upload_response = Mock()
        upload_response.json.return_value = {
            "code": 0,
            "data": {"image_key": "img_bytes_123"},
        }
        upload_response.raise_for_status = Mock()

        mock_post.side_effect = [token_response, upload_response]

        uploader = FeishuImageUploader("cli_test", "secret")
        image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        image_key = uploader.upload_image_bytes(image_bytes, "test.png")

        assert image_key == "img_bytes_123"

    @patch("httpx.Client.post")
    def test_upload_image_base64_success(self, mock_post):
        """Test uploading base64 encoded image."""
        token_response = Mock()
        token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        token_response.raise_for_status = Mock()

        upload_response = Mock()
        upload_response.json.return_value = {
            "code": 0,
            "data": {"image_key": "img_b64_123"},
        }
        upload_response.raise_for_status = Mock()

        mock_post.side_effect = [token_response, upload_response]

        uploader = FeishuImageUploader("cli_test", "secret")
        base64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        image_key = uploader.upload_image_base64(base64_data, "test.png")

        assert image_key == "img_b64_123"


# ==============================================================================
# Permission Error Handling Tests
# ==============================================================================


class TestPermissionErrorHandling:
    """Tests for permission error handling."""

    @patch("httpx.Client.post")
    def test_upload_permission_denied(self, mock_post):
        """Test upload with permission denied error."""
        token_response = Mock()
        token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        token_response.raise_for_status = Mock()

        upload_response = Mock()
        upload_response.json.return_value = {
            "code": 99991672,
            "msg": "Permission denied",
            "error": {
                "permission_violations": [
                    {"type": "action_scope_required", "subject": "im:resource"},
                ]
            },
        }
        upload_response.raise_for_status = Mock()

        mock_post.side_effect = [token_response, upload_response]

        uploader = FeishuImageUploader("cli_test", "secret")

        with pytest.raises(FeishuPermissionDeniedError) as exc_info:
            uploader.upload_image_bytes(b"test", "test.png")

        assert "im:resource" in exc_info.value.required_permissions

    @patch("httpx.Client.post")
    @patch.object(FeishuPermissionChecker, "open_auth_page")
    def test_upload_permission_denied_auto_open(self, mock_open_auth, mock_post):
        """Test auto-open browser on permission denied."""
        token_response = Mock()
        token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        token_response.raise_for_status = Mock()

        upload_response = Mock()
        upload_response.json.return_value = {
            "code": 99991672,
            "msg": "Permission denied",
            "error": {},
        }
        upload_response.raise_for_status = Mock()

        mock_post.side_effect = [token_response, upload_response]
        mock_open_auth.return_value = True

        uploader = FeishuImageUploader("cli_test", "secret", auto_open_auth=True)

        with pytest.raises(FeishuPermissionDeniedError):
            uploader.upload_image_bytes(b"test", "test.png")

        mock_open_auth.assert_called_once()


# ==============================================================================
# Helper Function Tests
# ==============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_auth_url(self):
        """Test uploader get_auth_url method."""
        uploader = FeishuImageUploader("cli_test", "secret")

        url = uploader.get_auth_url()

        assert "cli_test" in url
        assert "open.feishu.cn" in url

    def test_get_auth_url_custom_permissions(self):
        """Test get_auth_url with custom permissions."""
        uploader = FeishuImageUploader("cli_test", "secret")

        url = uploader.get_auth_url(permissions=["custom:permission"])

        assert "custom:permission" in url

    @patch.object(FeishuPermissionChecker, "open_auth_page")
    def test_open_auth_page(self, mock_open):
        """Test uploader open_auth_page method."""
        mock_open.return_value = True

        uploader = FeishuImageUploader("cli_test", "secret")
        result = uploader.open_auth_page()

        assert result is True
        mock_open.assert_called_once()


class TestCreateImageCard:
    """Tests for create_image_card helper function."""

    @patch("feishu_webhook_bot.core.client.CardBuilder")
    def test_create_image_card_basic(self, mock_builder_class):
        """Test creating basic image card."""
        mock_builder = Mock()
        mock_builder.build.return_value = {"type": "card"}
        mock_builder_class.return_value = mock_builder

        result = create_image_card("img_key_123")

        assert result == {"type": "card"}
        mock_builder.add_image.assert_called_once()

    @patch("feishu_webhook_bot.core.client.CardBuilder")
    def test_create_image_card_with_title(self, mock_builder_class):
        """Test creating image card with title."""
        mock_builder = Mock()
        mock_builder.build.return_value = {"type": "card"}
        mock_builder_class.return_value = mock_builder

        create_image_card("img_key_123", title="Test Title")

        mock_builder.set_header.assert_called_once_with("Test Title", template="default")

    @patch("feishu_webhook_bot.core.client.CardBuilder")
    def test_create_image_card_custom_options(self, mock_builder_class):
        """Test creating image card with custom options."""
        mock_builder = Mock()
        mock_builder.build.return_value = {"type": "card"}
        mock_builder_class.return_value = mock_builder

        create_image_card(
            "img_key_123",
            alt_text="Alt text",
            preview=False,
            scale_type="fit_horizontal",
        )

        mock_builder.add_image.assert_called_once_with(
            img_key="img_key_123",
            alt="Alt text",
            preview=False,
            scale_type="fit_horizontal",
        )
