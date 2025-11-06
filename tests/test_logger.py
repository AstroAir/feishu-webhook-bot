"""Tests for the logger module."""

import logging
import tempfile
from pathlib import Path

from feishu_webhook_bot.core.config import LoggingConfig
from feishu_webhook_bot.core.logger import get_logger, setup_logging


def test_get_logger():
    """Test getting a logger instance."""
    logger = get_logger("test")

    assert logger is not None
    assert logger.name == "feishu_bot.test"
    assert isinstance(logger, logging.Logger)


def test_get_logger_different_names():
    """Test getting loggers with different names."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")

    assert logger1.name == "feishu_bot.module1"
    assert logger2.name == "feishu_bot.module2"
    assert logger1 != logger2


def test_get_logger_same_name():
    """Test getting logger with same name returns same instance."""
    logger1 = get_logger("same")
    logger2 = get_logger("same")

    assert logger1 is logger2


def test_setup_logging_default():
    """Test setup logging with default config."""
    config = LoggingConfig()

    setup_logging(config)

    logger = get_logger("test")
    assert logger.level == logging.INFO


def test_setup_logging_debug_level():
    """Test setup logging with DEBUG level."""
    config = LoggingConfig(level="DEBUG")

    setup_logging(config)

    logger = get_logger("test_debug")
    # Root logger should be set to DEBUG
    root_logger = logging.getLogger("feishu_bot")
    assert root_logger.level == logging.DEBUG


def test_setup_logging_with_file():
    """Test setup logging with file output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        config = LoggingConfig(log_file=str(log_file))

        setup_logging(config)

        logger = get_logger("file_test")
        logger.info("Test message")

        # Log file should be created
        assert log_file.exists()


def test_setup_logging_different_formats():
    """Test logging with different format."""
    config = LoggingConfig(format="%(levelname)s - %(message)s")

    setup_logging(config)

    logger = get_logger("format_test")
    assert logger is not None


def test_logger_hierarchy():
    """Test logger hierarchy."""
    parent_logger = get_logger("parent")
    child_logger = get_logger("parent.child")

    assert child_logger.parent == parent_logger or child_logger.parent.name == parent_logger.name


def test_logging_levels():
    """Test different logging levels."""
    logger = get_logger("levels_test")

    # Should not raise errors
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")


def test_setup_logging_info_level():
    """Test setup logging with INFO level."""
    config = LoggingConfig(level="INFO")

    setup_logging(config)

    root_logger = logging.getLogger("feishu_bot")
    assert root_logger.level == logging.INFO


def test_setup_logging_warning_level():
    """Test setup logging with WARNING level."""
    config = LoggingConfig(level="WARNING")

    setup_logging(config)

    root_logger = logging.getLogger("feishu_bot")
    assert root_logger.level == logging.WARNING


def test_setup_logging_error_level():
    """Test setup logging with ERROR level."""
    config = LoggingConfig(level="ERROR")

    setup_logging(config)

    root_logger = logging.getLogger("feishu_bot")
    assert root_logger.level == logging.ERROR
