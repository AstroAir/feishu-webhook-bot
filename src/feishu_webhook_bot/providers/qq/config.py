"""Configuration classes for QQ/Napcat providers.

This module contains all configuration classes used by QQ providers.
"""

from __future__ import annotations

from pydantic import Field

from ...core.provider import ProviderConfig


class NapcatProviderConfig(ProviderConfig):
    """Configuration for QQ Napcat provider (OneBot11 protocol).

    Attributes:
        provider_type: Provider type identifier (default: "napcat").
        http_url: Napcat HTTP API base URL.
        access_token: Optional API access token for authentication.
        bot_qq: Bot's QQ number for @mention detection.
        enable_ai_voice: Enable NapCat AI voice features.

    Example:
        ```python
        config = NapcatProviderConfig(
            name="my_qq_bot",
            http_url="http://127.0.0.1:3000",
            access_token="your_token",
            bot_qq="123456789",
        )
        ```
    """

    provider_type: str = Field(default="napcat", description="Provider type")
    http_url: str = Field(
        ...,
        description="Napcat HTTP API base URL (e.g., http://127.0.0.1:3000)",
    )
    access_token: str | None = Field(
        default=None,
        description="Optional Napcat API access token for authentication",
    )
    bot_qq: str | None = Field(
        default=None,
        description="Bot's QQ number for @mention detection",
    )
    enable_ai_voice: bool = Field(
        default=False,
        description="Enable NapCat AI voice features",
    )
