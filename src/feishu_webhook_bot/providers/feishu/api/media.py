"""File and media API operations for Feishu.

This module provides file and media operations:
- Upload images
- Download images
- Upload files
- Download files
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from ....core.logger import get_logger
from .models import FeishuAPIError

if TYPE_CHECKING:
    pass

logger = get_logger("feishu_api.media")


class FeishuMediaMixin:
    """Mixin providing file/media functionality for Feishu API.

    This mixin should be used with a class that has:
    - self._ensure_client() -> httpx.AsyncClient
    - self.get_tenant_access_token() -> str
    """

    # API endpoints
    UPLOAD_IMAGE_URL = "/im/v1/images"
    GET_IMAGE_URL = "/im/v1/images/{image_key}"
    UPLOAD_FILE_URL = "/im/v1/files"
    GET_FILE_URL = "/im/v1/files/{file_key}"

    def _ensure_client(self) -> Any:
        """Ensure HTTP client is initialized. To be implemented by main class."""
        raise NotImplementedError

    async def get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """Get tenant access token. To be implemented by main class."""
        raise NotImplementedError

    async def upload_image(
        self,
        image: bytes,
        image_type: Literal["message", "avatar"] = "message",
    ) -> str:
        """Upload an image to Feishu.

        Args:
            image: Image content as bytes.
            image_type: Image type ("message" for chat images, "avatar" for avatars).

        Returns:
            Image key for use in messages.

        Raises:
            FeishuAPIError: If upload fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        response = await client.post(
            self.UPLOAD_IMAGE_URL,
            headers={"Authorization": f"Bearer {token}"},
            data={"image_type": image_type},
            files={"image": ("image.png", image, "image/png")},
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        image_key = data.get("data", {}).get("image_key", "")
        logger.info("Image uploaded: %s", image_key)
        return image_key

    async def download_image(self, image_key: str) -> bytes:
        """Download an image by its key.

        Args:
            image_key: Image key from message or upload.

        Returns:
            Image content as bytes.

        Raises:
            FeishuAPIError: If download fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.GET_IMAGE_URL.format(image_key=image_key)
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise FeishuAPIError(
                code=response.status_code,
                msg=f"Failed to download image: {response.text}",
            )

        return response.content

    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        file_type: Literal["opus", "mp4", "pdf", "doc", "xls", "ppt", "stream"] = "stream",
    ) -> str:
        """Upload a file to Feishu.

        Args:
            file_content: File content as bytes.
            file_name: Original file name.
            file_type: File type category.

        Returns:
            File key for use in messages.

        Raises:
            FeishuAPIError: If upload fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        response = await client.post(
            self.UPLOAD_FILE_URL,
            headers={"Authorization": f"Bearer {token}"},
            data={"file_type": file_type, "file_name": file_name},
            files={"file": (file_name, file_content, "application/octet-stream")},
        )

        data = response.json()
        if data.get("code") != 0:
            raise FeishuAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
            )

        file_key = data.get("data", {}).get("file_key", "")
        logger.info("File uploaded: %s", file_key)
        return file_key

    async def download_file(self, file_key: str) -> bytes:
        """Download a file by its key.

        Args:
            file_key: File key from message or upload.

        Returns:
            File content as bytes.

        Raises:
            FeishuAPIError: If download fails.
        """
        client = self._ensure_client()
        token = await self.get_tenant_access_token()

        url = self.GET_FILE_URL.format(file_key=file_key)
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise FeishuAPIError(
                code=response.status_code,
                msg=f"Failed to download file: {response.text}",
            )

        return response.content
