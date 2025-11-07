"""Tests for the logger module."""

import logging

import pytest
from rich.logging import RichHandler

from feishu_webhook_bot.core.config import LoggingConfig
from feishu_webhook_bot.core.logger import (
    CloseOnEmitFileHandler,
    get_logger,
    log_exception,
    setup_logging,
)


@pytest.fixture(autouse=True)
def reset_logging():
    """Fixture to reset logging configuration before and after each test."""
    # Before test: save original state
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level

    yield

    # After test: restore original state
    logging.root.handlers = original_handlers
    logging.root.setLevel(original_level)
    # Clear the internal logger cache in our module
    from feishu_webhook_bot.core import logger

    logger._loggers.clear()
    logger._configured = False


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_get_logger_returns_correct_instance(self):
        """Test that get_logger returns a correctly named Logger instance."""
        logger = get_logger("test_name")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "feishu_bot.test_name"

    def test_get_logger_is_cached(self):
        """Test that multiple calls with the same name return the same logger instance."""
        logger1 = get_logger("cached_name")
        logger2 = get_logger("cached_name")
        assert logger1 is logger2


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_setup_logging_levels(self):
        """Test that setup_logging correctly sets the logger level."""
        setup_logging(LoggingConfig(level="DEBUG"))
        root_logger = logging.getLogger("feishu_bot")
        assert root_logger.level == logging.DEBUG

        setup_logging(LoggingConfig(level="WARNING"))
        assert root_logger.level == logging.WARNING

    def test_setup_logging_handlers(self, tmp_path):
        """Test that the correct handlers are configured."""
        # 1. Test with console logging only
        setup_logging(LoggingConfig(log_file=None))
        root_handlers = logging.getLogger().handlers
        assert len(root_handlers) == 1
        assert isinstance(root_handlers[0], RichHandler)

        # 2. Test with file logging
        log_file = tmp_path / "test.log"
        setup_logging(LoggingConfig(log_file=str(log_file)))
        root_handlers = logging.getLogger().handlers
        assert len(root_handlers) == 2
        assert any(isinstance(h, RichHandler) for h in root_handlers)
        assert any(isinstance(h, CloseOnEmitFileHandler) for h in root_handlers)

    def test_file_logging_writes_to_file(self, tmp_path):
        """Test that file logging actually writes messages to the specified file."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(level="INFO", log_file=str(log_file))
        setup_logging(config)

        logger = get_logger("file_test")
        test_message = "This is a test message for the log file."
        logger.info(test_message)

        # The custom file handler closes the file after emit, so we can read it.
        assert log_file.exists()
        log_content = log_file.read_text()
        assert test_message in log_content

    def test_log_exception_helper(self, caplog):
        """Test the log_exception helper function."""
        logger = get_logger("exception_test")

        try:
            raise ValueError("A test exception")
        except ValueError as e:
            log_exception(logger, e, context="During testing")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "ERROR"
        assert "During testing: A test exception" in record.message
        assert record.exc_info is not None
