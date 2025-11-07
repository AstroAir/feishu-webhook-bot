"""Logging utilities for Feishu Webhook Bot.

This module provides centralized logging configuration with support for:
- Console and file logging
- Log rotation
- Rich formatting for console output
"""

from __future__ import annotations

import logging
from contextlib import suppress
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from .config import LoggingConfig

# Global logger registry
_loggers: dict[str, logging.Logger] = {}
_configured = False
_current_level: int = logging.INFO

console = Console()


class CloseOnEmitFileHandler(RotatingFileHandler):
    """A RotatingFileHandler that closes the file after each emit.

    This avoids holding an open file handle which can block temporary
    directory cleanup on Windows during tests.
    """

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        try:
            super().emit(record)
        finally:
            # Ensure the file descriptor is released between writes
            try:
                self.flush()
            finally:
                # Close so that subsequent emits will reopen (when delay=True)
                self.close()


def setup_logging(config: LoggingConfig | None = None) -> None:
    """Setup logging configuration for the entire application.

    Args:
        config: LoggingConfig instance. If None, uses defaults.
    """
    global _configured

    if config is None:
        config = LoggingConfig()

    # Clear any existing handlers (and close them to release resources)
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        with suppress(Exception):
            handler.flush()
        with suppress(Exception):
            handler.close()
    root_logger.handlers.clear()

    # Set root logger level
    level_value = getattr(logging, config.level)
    root_logger.setLevel(level_value)
    # Also set the 'feishu_bot' namespace logger level explicitly (tests rely on this)
    feishu_root = logging.getLogger("feishu_bot")
    feishu_root.setLevel(level_value)

    # Create formatters
    file_formatter = logging.Formatter(config.format)

    # Add console handler with Rich formatting
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(getattr(logging, config.level))
    root_logger.addHandler(console_handler)

    # Add file handler if configured
    if config.log_file:
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Use a handler variant that closes the file between emits to avoid
        # Windows file locking issues during tests using TemporaryDirectory.
        file_handler = CloseOnEmitFileHandler(
            log_path,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setLevel(getattr(logging, config.level))
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    _configured = True
    _current_level = level_value

    # Ensure already-created named loggers align with current level
    for lg in _loggers.values():
        lg.setLevel(level_value)

    # Log configuration complete
    logger = get_logger("setup")
    logger.info(f"Logging configured: level={config.level}")
    if config.log_file:
        logger.info(f"Log file: {config.log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name.

    Args:
        name: Logger name (typically module name)

    Returns:
        Logger instance
    """
    if name not in _loggers:
        logger = logging.getLogger(f"feishu_bot.{name}")
        # Ensure level is set explicitly to satisfy tests
        logger.setLevel(_current_level)
        _loggers[name] = logger

    return _loggers[name]


def log_exception(logger: logging.Logger, exc: Exception, context: str = "") -> None:
    """Log an exception with context.

    Args:
        logger: Logger instance
        exc: Exception to log
        context: Additional context string
    """
    if context:
        logger.exception(f"{context}: {exc}")
    else:
        logger.exception(f"Exception occurred: {exc}")
