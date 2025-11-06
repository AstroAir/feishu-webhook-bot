"""Feishu Webhook Bot Framework.

A production-ready framework for building Feishu (Lark) webhook bots with:
- Message sending (text, rich text, interactive cards, images)
- Task scheduling and workflows
- Extensible plugin system
- Hot-reload support
- Comprehensive configuration management

Example:
    ```python
    from feishu_webhook_bot import FeishuBot

    # Start bot with config file
    bot = FeishuBot.from_config("config.yaml")
    bot.start()

    # Or create programmatically
    from feishu_webhook_bot.core import BotConfig, WebhookConfig

    config = BotConfig(
        webhooks=[WebhookConfig(url="https://...", secret="...")]
    )
    bot = FeishuBot(config)
    bot.start()
    ```
"""

from importlib.metadata import PackageNotFoundError, version

from .bot import FeishuBot
from .core import (
    BotConfig,
    FeishuWebhookClient,
    WebhookConfig,
    get_logger,
    setup_logging,
)
from .plugins import BasePlugin, PluginManager, PluginMetadata
from .scheduler import TaskScheduler, job

__all__ = [
    "__version__",
    "FeishuBot",
    "BotConfig",
    "WebhookConfig",
    "FeishuWebhookClient",
    "TaskScheduler",
    "job",
    "BasePlugin",
    "PluginMetadata",
    "PluginManager",
    "get_logger",
    "setup_logging",
]

try:  # pragma: no cover - best-effort during development
    __version__ = version("feishu-webhook-bot")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

