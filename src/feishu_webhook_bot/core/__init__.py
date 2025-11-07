"""Core modules for Feishu Webhook Bot framework.

This package contains the core functionality including:
- Webhook client for sending messages
- Configuration management
- Logging utilities
"""

from .client import FeishuWebhookClient
from .config import AuthConfig, BotConfig, WebhookConfig
from .logger import get_logger, setup_logging

__all__ = [
    "FeishuWebhookClient",
    "BotConfig",
    "WebhookConfig",
    "AuthConfig",
    "get_logger",
    "setup_logging",
]
