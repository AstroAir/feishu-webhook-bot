"""Configuration classes for Feishu providers.

This module contains all configuration classes used by Feishu providers.
"""

from __future__ import annotations

from pydantic import Field

from ...core.provider import ProviderConfig


class FeishuProviderConfig(ProviderConfig):
    """Configuration for Feishu webhook provider.

    Attributes:
        provider_type: Provider type identifier (default: "feishu").
        url: Feishu webhook URL.
        secret: Optional webhook secret for HMAC-SHA256 signing.
        headers: Additional HTTP headers to include in requests.

    Example:
        ```python
        config = FeishuProviderConfig(
            name="my_bot",
            url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
            secret="your_secret",
        )
        ```
    """

    provider_type: str = Field(default="feishu", description="Provider type")
    url: str = Field(..., description="Feishu webhook URL")
    secret: str | None = Field(
        default=None,
        description="Webhook secret for HMAC-SHA256 signing",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers",
    )
