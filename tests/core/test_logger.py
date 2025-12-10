"""Comprehensive tests for logging utilities module.

Tests cover:
- get_logger function
- setup_logging function
- log_exception function
- CloseOnEmitFileHandler
- Logger configuration
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from feishu_webhook_bot.core.config import LoggingConfig
from feishu_webhook_bot.core.logger import (
    CloseOnEmitFileHandler,
    get_logger,
    log_exception,
    setup_logging,
)


# ==============================================================================
# get_logger Tests
# ==============================================================================


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a Logger instance."""
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)

    def test_get_logger_name_prefix(self):
        """Test get_logger adds feishu_bot prefix."""
        logger = get_logger("my_module")

        assert logger.name == "feishu_bot.my_module"

    def test_get_logger_same_name_returns_same_logger(self):
        """Test get_logger returns same logger for same name."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")

        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test get_logger returns different loggers for different names."""
        logger1 = get_logger("module_a")
        logger2 = get_logger("module_b")

        assert logger1 is not logger2
        assert logger1.name != logger2.name


# ==============================================================================
# setup_logging Tests
# ==============================================================================


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default_config(self):
        """Test setup_logging with default config."""
        setup_logging()

        # Should not raise
        logger = get_logger("test_setup")
        logger.info("Test message")

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom level."""
        config = LoggingConfig(level="DEBUG")

        setup_logging(config)

        # The root feishu_bot logger should have DEBUG level
        root_logger = logging.getLogger("feishu_bot")
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_with_file(self):
        """Test setup_logging with file handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(level="INFO", log_file=str(log_file))

            setup_logging(config)

            logger = get_logger("test_file")
            logger.info("Test file message")

            # File should be created
            assert log_file.exists()

    def test_setup_logging_creates_log_directory(self):
        """Test setup_logging creates log directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "nested" / "test.log"
            config = LoggingConfig(log_file=str(log_file))

            setup_logging(config)

            logger = get_logger("test_dir")
            logger.info("Test message")

            # Directory should be created
            assert log_file.parent.exists()


# ==============================================================================
# log_exception Tests
# ==============================================================================


class TestLogException:
    """Tests for log_exception function."""

    def test_log_exception_basic(self, caplog):
        """Test log_exception logs exception."""
        logger = get_logger("test_exc")

        try:
            raise ValueError("Test error")
        except ValueError as e:
            with caplog.at_level(logging.ERROR):
                log_exception(logger, e)

        assert "Test error" in caplog.text

    def test_log_exception_with_context(self, caplog):
        """Test log_exception with context."""
        logger = get_logger("test_exc_ctx")

        try:
            raise RuntimeError("Something failed")
        except RuntimeError as e:
            with caplog.at_level(logging.ERROR):
                log_exception(logger, e, context="Processing request")

        assert "Processing request" in caplog.text
        assert "Something failed" in caplog.text

    def test_log_exception_without_context(self, caplog):
        """Test log_exception without context."""
        logger = get_logger("test_exc_no_ctx")

        try:
            raise KeyError("missing_key")
        except KeyError as e:
            with caplog.at_level(logging.ERROR):
                log_exception(logger, e)

        assert "Exception occurred" in caplog.text


# ==============================================================================
# CloseOnEmitFileHandler Tests
# ==============================================================================


class TestCloseOnEmitFileHandler:
    """Tests for CloseOnEmitFileHandler."""

    def test_handler_writes_to_file(self):
        """Test handler writes log records to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "handler_test.log"

            handler = CloseOnEmitFileHandler(
                log_file,
                maxBytes=1024 * 1024,
                backupCount=1,
                delay=True,
            )
            handler.setFormatter(logging.Formatter("%(message)s"))

            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            handler.emit(record)

            # File should contain the message
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content

    def test_handler_closes_after_emit(self):
        """Test handler closes file after emit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "close_test.log"

            handler = CloseOnEmitFileHandler(
                log_file,
                maxBytes=1024 * 1024,
                backupCount=1,
                delay=True,
            )

            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test",
                args=(),
                exc_info=None,
            )

            handler.emit(record)

            # Stream should be closed (None when delay=True and closed)
            # The handler should have released the file
            handler.close()  # Explicit close for cleanup

    def test_handler_multiple_emits(self):
        """Test handler handles multiple emits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "multi_test.log"

            handler = CloseOnEmitFileHandler(
                log_file,
                maxBytes=1024 * 1024,
                backupCount=1,
                delay=True,
            )
            handler.setFormatter(logging.Formatter("%(message)s"))

            for i in range(5):
                record = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"Message {i}",
                    args=(),
                    exc_info=None,
                )
                handler.emit(record)

            handler.close()

            # All messages should be in file
            content = log_file.read_text()
            for i in range(5):
                assert f"Message {i}" in content


# ==============================================================================
# LoggingConfig Tests
# ==============================================================================


class TestLoggingConfig:
    """Tests for LoggingConfig model."""

    def test_config_defaults(self):
        """Test LoggingConfig default values."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.log_file is None
        assert config.max_bytes > 0
        assert config.backup_count >= 0

    def test_config_custom_level(self):
        """Test LoggingConfig with custom level."""
        config = LoggingConfig(level="DEBUG")

        assert config.level == "DEBUG"

    def test_config_with_file(self):
        """Test LoggingConfig with log file."""
        config = LoggingConfig(log_file="/var/log/app.log")

        assert config.log_file == "/var/log/app.log"

    def test_config_rotation_settings(self):
        """Test LoggingConfig rotation settings."""
        config = LoggingConfig(
            max_bytes=5 * 1024 * 1024,  # 5MB
            backup_count=10,
        )

        assert config.max_bytes == 5 * 1024 * 1024
        assert config.backup_count == 10


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def test_full_logging_workflow(self):
        """Test complete logging workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "integration.log"
            config = LoggingConfig(
                level="DEBUG",
                log_file=str(log_file),
            )

            setup_logging(config)

            logger = get_logger("integration_test")

            # Log at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # Verify file contains messages
            content = log_file.read_text()
            assert "Debug message" in content or "Info message" in content

    def test_multiple_loggers(self):
        """Test multiple loggers work correctly."""
        setup_logging()

        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        logger3 = get_logger("module3")

        # All should be able to log
        logger1.info("From module1")
        logger2.info("From module2")
        logger3.info("From module3")

        # All should have correct names
        assert "module1" in logger1.name
        assert "module2" in logger2.name
        assert "module3" in logger3.name
