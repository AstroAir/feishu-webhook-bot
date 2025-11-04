"""Top-level package for feishu_webhook_bot.

This package provides a minimal example package for a Feishu (Lark) Webhook bot.
It is intentionally small and intended as a starter/template for building webhook
handlers and integration logic.
"""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:  # pragma: no cover - best-effort during development
    __version__ = version("feishu-webhook-bot")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

