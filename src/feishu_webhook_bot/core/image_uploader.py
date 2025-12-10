"""Image uploader for Feishu Open Platform.

This module provides functionality to upload images to Feishu and obtain image_key
for use in webhook messages.

Note: Image upload requires a Feishu application with appropriate permissions.
For simple webhook-only use cases, consider using rich text messages with links
or the base64 fallback methods.
"""

from __future__ import annotations

import base64
import mimetypes
import platform
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from .logger import get_logger

logger = get_logger("image_uploader")


# Common Feishu API error codes
PERMISSION_DENIED_CODE = 99991672
INVALID_TOKEN_CODE = 99991663
INVALID_APP_CODE = 10003


@dataclass
class PermissionError:
    """Represents a Feishu permission error with resolution info."""

    code: int
    message: str
    required_permissions: list[str]
    auth_url: str | None = None

    def __str__(self) -> str:
        perms = ", ".join(self.required_permissions)
        return f"Permission denied. Required: [{perms}]. Auth URL: {self.auth_url}"


class FeishuPermissionChecker:
    """Check and manage Feishu application permissions.

    This class helps detect missing permissions and provides URLs to
    configure them in the Feishu Open Platform.
    """

    # Permission scopes for different features
    PERMISSIONS = {
        "image_upload": ["im:resource", "im:resource:upload"],
        "file_upload": ["im:resource", "im:resource:upload"],
        "message_send": ["im:message", "im:message:send_as_bot"],
        "calendar_read": ["calendar:calendar", "calendar:calendar:readonly"],
    }

    AUTH_URL_TEMPLATE = (
        "https://open.feishu.cn/app/{app_id}/auth"
        "?q={permissions}&op_from=openapi&token_type=tenant"
    )

    @classmethod
    def get_auth_url(cls, app_id: str, permissions: list[str]) -> str:
        """Generate the authorization URL for requesting permissions.

        Args:
            app_id: Feishu application ID
            permissions: List of permission scopes to request

        Returns:
            URL to open in browser for permission configuration
        """
        perms_str = ",".join(permissions)
        return cls.AUTH_URL_TEMPLATE.format(app_id=app_id, permissions=perms_str)

    @classmethod
    def get_app_config_url(cls, app_id: str) -> str:
        """Get the URL to the app's configuration page.

        Args:
            app_id: Feishu application ID

        Returns:
            URL to the app configuration page
        """
        return f"https://open.feishu.cn/app/{app_id}/auth"

    @classmethod
    def parse_permission_error(
        cls, response_data: dict[str, Any], app_id: str
    ) -> PermissionError | None:
        """Parse API response to extract permission error details.

        Args:
            response_data: JSON response from Feishu API
            app_id: Feishu application ID

        Returns:
            PermissionError if this is a permission error, None otherwise
        """
        code = response_data.get("code")
        if code != PERMISSION_DENIED_CODE:
            return None

        msg = response_data.get("msg", "")
        error_detail = response_data.get("error", {})

        # Extract required permissions from error
        required_perms = []
        violations = error_detail.get("permission_violations", [])
        for v in violations:
            if v.get("type") == "action_scope_required":
                required_perms.append(v.get("subject", ""))

        # If no specific permissions found, use defaults for image upload
        if not required_perms:
            required_perms = cls.PERMISSIONS["image_upload"]

        auth_url = cls.get_auth_url(app_id, required_perms)

        return PermissionError(
            code=code,
            message=msg,
            required_permissions=required_perms,
            auth_url=auth_url,
        )

    @classmethod
    def open_auth_page(cls, url: str, silent: bool = False) -> bool:
        """Open the authorization page in the default browser.

        Args:
            url: URL to open
            silent: If True, suppress error messages

        Returns:
            True if browser was opened successfully
        """
        try:
            # Try webbrowser first (cross-platform)
            if webbrowser.open(url):
                logger.info("Opened browser for permission configuration: %s", url)
                return True
        except Exception as e:
            if not silent:
                logger.warning("Failed to open browser via webbrowser: %s", e)

        # Platform-specific fallbacks
        system = platform.system().lower()
        try:
            if system == "darwin":  # macOS
                subprocess.run(["open", url], check=True)
                return True
            elif system == "windows":
                subprocess.run(["start", "", url], shell=True, check=True)
                return True
            elif system == "linux":
                subprocess.run(["xdg-open", url], check=True)
                return True
        except Exception as e:
            if not silent:
                logger.warning("Failed to open browser: %s", e)

        return False


class FeishuImageUploaderError(Exception):
    """Base exception for FeishuImageUploader errors."""

    pass


class FeishuPermissionDeniedError(FeishuImageUploaderError):
    """Raised when the app lacks required permissions."""

    def __init__(
        self,
        message: str,
        required_permissions: list[str],
        auth_url: str | None = None,
    ):
        super().__init__(message)
        self.required_permissions = required_permissions
        self.auth_url = auth_url


class FeishuImageUploader:
    """Upload images to Feishu and obtain image_key.

    This class handles the process of:
    1. Obtaining tenant_access_token using app credentials
    2. Uploading images to Feishu
    3. Returning image_key for use in messages
    4. Auto-detecting permission errors and opening config page

    Example:
        ```python
        uploader = FeishuImageUploader(
            app_id="cli_xxx",
            app_secret="xxx",
            auto_open_auth=True  # Auto-open browser on permission error
        )

        # Upload from file
        image_key = uploader.upload_image("path/to/image.png")

        # Use in webhook message
        client.send_image(image_key)
        ```

    Note:
        Requires the following Feishu application permissions:
        - im:resource (Upload/download images and files)
    """

    # Feishu API endpoints
    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    UPLOAD_URL = "https://open.feishu.cn/open-apis/im/v1/images"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        timeout: float = 30.0,
        auto_open_auth: bool = False,
    ):
        """Initialize the image uploader.

        Args:
            app_id: Feishu application ID
            app_secret: Feishu application secret
            timeout: HTTP request timeout in seconds
            auto_open_auth: If True, automatically open browser to permission
                           configuration page when permission errors occur
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout = timeout
        self.auto_open_auth = auto_open_auth
        self._token: str | None = None
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> FeishuImageUploader:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """Obtain tenant_access_token from Feishu.

        Args:
            force_refresh: Force refresh token even if cached

        Returns:
            Tenant access token string

        Raises:
            ValueError: If token request fails
        """
        if self._token and not force_refresh:
            return self._token

        logger.debug("Requesting tenant_access_token")

        response = self._client.post(
            self.TOKEN_URL,
            json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
        )
        response.raise_for_status()

        data = response.json()
        if data.get("code") != 0:
            raise ValueError(f"Failed to get token: {data.get('msg')}")

        self._token = data["tenant_access_token"]
        logger.info("Successfully obtained tenant_access_token")
        return self._token

    def _handle_api_response(
        self, response: httpx.Response, operation: str = "API call"
    ) -> dict[str, Any]:
        """Handle API response and check for permission errors.

        Args:
            response: HTTP response from Feishu API
            operation: Description of the operation for error messages

        Returns:
            Parsed JSON response data

        Raises:
            FeishuPermissionDeniedError: If permission is denied (with auto-open option)
            FeishuImageUploaderError: For other API errors
        """
        # Try to parse JSON even for error responses
        try:
            result = response.json()
        except Exception:
            response.raise_for_status()
            raise FeishuImageUploaderError(f"{operation} failed: Unable to parse response")

        code = result.get("code", 0)

        # Success
        if code == 0:
            return result

        # Check for permission error
        perm_error = FeishuPermissionChecker.parse_permission_error(result, self.app_id)
        if perm_error:
            logger.error(
                "Permission denied for %s. Required permissions: %s",
                operation,
                perm_error.required_permissions,
            )

            # Auto-open browser if enabled
            if self.auto_open_auth and perm_error.auth_url:
                logger.info(
                    "Opening browser for permission configuration: %s",
                    perm_error.auth_url,
                )
                FeishuPermissionChecker.open_auth_page(perm_error.auth_url)

            raise FeishuPermissionDeniedError(
                message=str(perm_error),
                required_permissions=perm_error.required_permissions,
                auth_url=perm_error.auth_url,
            )

        # Other errors
        error_msg = result.get("msg", "Unknown error")
        raise FeishuImageUploaderError(f"{operation} failed: {error_msg} (code: {code})")

    def check_permissions(self) -> bool:
        """Check if the app has required permissions for image upload.

        This method attempts a minimal API call to verify permissions.
        If permissions are missing and auto_open_auth is True, it will
        open the browser to the configuration page.

        Returns:
            True if permissions are available

        Raises:
            FeishuPermissionDeniedError: If permissions are missing
        """
        logger.debug("Checking image upload permissions for app: %s", self.app_id)

        # Get token first
        token = self._get_tenant_access_token()

        # Try to upload a minimal test image (1x1 transparent PNG)
        # Base64: iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
        test_image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        files = {
            "image": ("test.png", test_image, "image/png"),
        }
        data = {
            "image_type": "message",
        }

        response = self._client.post(
            self.UPLOAD_URL,
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
        )

        # This will raise FeishuPermissionDeniedError if permissions are missing
        self._handle_api_response(response, "permission check")
        logger.info("Permission check passed for app: %s", self.app_id)
        return True

    def get_auth_url(self, permissions: list[str] | None = None) -> str:
        """Get the URL to configure permissions for this app.

        Args:
            permissions: Specific permissions to request (defaults to image upload)

        Returns:
            URL to open in browser
        """
        if permissions is None:
            permissions = FeishuPermissionChecker.PERMISSIONS["image_upload"]
        return FeishuPermissionChecker.get_auth_url(self.app_id, permissions)

    def open_auth_page(self, permissions: list[str] | None = None) -> bool:
        """Open the browser to the permission configuration page.

        Args:
            permissions: Specific permissions to request (defaults to image upload)

        Returns:
            True if browser was opened successfully
        """
        url = self.get_auth_url(permissions)
        return FeishuPermissionChecker.open_auth_page(url)

    def upload_image(
        self,
        file_path: str | Path,
        image_type: Literal["message", "avatar"] = "message",
    ) -> str:
        """Upload an image file to Feishu.

        Args:
            file_path: Path to the image file
            image_type: Image type - "message" for sending messages,
                        "avatar" for setting avatars

        Returns:
            image_key string for use in messages

        Raises:
            FileNotFoundError: If image file doesn't exist
            FeishuPermissionDeniedError: If app lacks required permissions
            FeishuImageUploaderError: If upload fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "application/octet-stream"

        logger.debug("Uploading image: %s (type: %s)", path.name, mime_type)

        # Get token
        token = self._get_tenant_access_token()

        # Upload image
        with open(path, "rb") as f:
            files = {
                "image": (path.name, f, mime_type),
            }
            data = {
                "image_type": image_type,
            }

            response = self._client.post(
                self.UPLOAD_URL,
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=data,
            )

        result = self._handle_api_response(response, f"upload image '{path.name}'")
        image_key = result["data"]["image_key"]
        logger.info("Image uploaded successfully: %s -> %s", path.name, image_key)
        return image_key

    def upload_image_bytes(
        self,
        image_data: bytes,
        filename: str = "image.png",
        mime_type: str | None = None,
        image_type: Literal["message", "avatar"] = "message",
    ) -> str:
        """Upload image bytes directly to Feishu.

        Args:
            image_data: Raw image bytes
            filename: Filename for the upload
            mime_type: MIME type (auto-detected if not provided)
            image_type: Image type - "message" or "avatar"

        Returns:
            image_key string for use in messages

        Raises:
            FeishuPermissionDeniedError: If app lacks required permissions
            FeishuImageUploaderError: If upload fails
        """
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = "image/png"

        logger.debug("Uploading image bytes: %s (type: %s)", filename, mime_type)

        token = self._get_tenant_access_token()

        files = {
            "image": (filename, image_data, mime_type),
        }
        data = {
            "image_type": image_type,
        }

        response = self._client.post(
            self.UPLOAD_URL,
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
        )

        result = self._handle_api_response(response, f"upload image bytes '{filename}'")
        image_key = result["data"]["image_key"]
        logger.info("Image bytes uploaded successfully: %s", image_key)
        return image_key

    def upload_image_base64(
        self,
        base64_data: str,
        filename: str = "image.png",
        mime_type: str | None = None,
        image_type: Literal["message", "avatar"] = "message",
    ) -> str:
        """Upload a base64-encoded image to Feishu.

        Args:
            base64_data: Base64-encoded image data (without data URI prefix)
            filename: Filename for the upload
            mime_type: MIME type (auto-detected if not provided)
            image_type: Image type - "message" or "avatar"

        Returns:
            image_key string for use in messages
        """
        # Decode base64
        image_bytes = base64.b64decode(base64_data)
        return self.upload_image_bytes(image_bytes, filename, mime_type, image_type)


def create_image_card(
    image_key: str,
    title: str | None = None,
    alt_text: str = "",
    preview: bool = True,
    scale_type: str = "crop_center",
) -> dict[str, Any]:
    """Create a card with an image.

    This is a convenience function to create a card structure containing an image.

    Args:
        image_key: Feishu image key
        title: Optional card title
        alt_text: Alternative text for the image
        preview: Enable click to preview
        scale_type: Image scaling mode

    Returns:
        Card structure ready to send
    """
    from .client import CardBuilder

    builder = CardBuilder()

    if title:
        builder.set_header(title, template="default")

    builder.add_image(
        img_key=image_key,
        alt=alt_text,
        preview=preview,
        scale_type=scale_type,
    )

    return builder.build()
