"""Tests for the command-line interface."""

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot import __version__
from feishu_webhook_bot import cli as cli_module
from feishu_webhook_bot.cli import main


@pytest.fixture
def mock_bot():
    """Fixture to mock the FeishuBot class."""
    with patch("feishu_webhook_bot.cli.FeishuBot") as mock_bot_class:
        mock_bot_instance = MagicMock()
        mock_bot_class.from_config.return_value = mock_bot_instance
        yield mock_bot_instance


class TestCliParsing:
    """Tests for the argument parsing logic."""

    def test_no_args_prints_help(self, capsys):
        """Test that running with no arguments prints help and exits."""
        with pytest.raises(SystemExit) as e:
            main([])
        assert e.value.code == 0
        captured = capsys.readouterr()
        assert "usage: feishu-webhook-bot" in captured.out

    def test_version_flag(self, capsys):
        """Test the -v / --version flag."""
        with pytest.raises(SystemExit) as e:
            main(["--version"])
        assert e.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out

    def test_start_command_args(self):
        """Test parsing for the 'start' command."""
        with patch(
            "argparse._sys.argv",
            ["prog", "start", "-c", "my.yaml", "--host", "0.0.0.0", "-p", "9999", "-d"],
        ):
            parser = cli_module.build_parser()
            args = parser.parse_args()
            assert args.command == "start"
            assert args.config == "my.yaml"
            assert args.host == "0.0.0.0"
            assert args.port == 9999
            assert args.debug is True

    def test_webui_command_args(self):
        """Test parsing for the 'webui' command."""
        with patch(
            "argparse._sys.argv",
            ["prog", "webui", "-c", "ui.yaml", "--host", "1.2.3.4", "--port", "1234"],
        ):
            parser = cli_module.build_parser()
            args = parser.parse_args()
            assert args.command == "webui"
            assert args.config == "ui.yaml"
            assert args.host == "1.2.3.4"
            assert args.port == 1234


class TestCliCommands:
    """Tests for the logic of each CLI command."""

    def test_main_start_command(self, mock_bot, tmp_path):
        """Test that the 'start' command loads config and starts the bot."""
        config_file = tmp_path / "config.yaml"
        config_file.touch()

        exit_code = main(["start", "-c", str(config_file)])

        assert exit_code == 0
        # Check that from_config was called, not the constructor directly
        mock_bot.from_config.assert_called_once_with(config_file)
        mock_bot.start.assert_called_once()

    def test_main_start_debug_flag(self, mocker, tmp_path):
        """Test that the --debug flag overrides the log level in the config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("logging:\n  level: INFO")

        mock_bot_class = mocker.patch("feishu_webhook_bot.cli.FeishuBot")
        mock_config_class = mocker.patch("feishu_webhook_bot.cli.BotConfig")
        # Create a mock config object that we can inspect
        mock_config_instance = MagicMock()
        mock_config_class.from_yaml.return_value = mock_config_instance

        main(["start", "-c", str(config_file), "--debug"])

        # Assert that the level was changed to DEBUG before initializing the bot
        assert mock_config_instance.logging.level == "DEBUG"
        mock_bot_class.assert_called_once_with(mock_config_instance)

    def test_main_start_file_not_found(self, capsys):
        """Test that 'start' exits gracefully if config file is not found."""
        exit_code = main(["start", "-c", "nonexistent.yaml"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Configuration file not found" in captured.out

    def test_main_init_command(self, tmp_path):
        """Test that the 'init' command creates a config file."""
        config_path = tmp_path / "test_config.yaml"
        exit_code = main(["init", "-o", str(config_path)])
        assert exit_code == 0
        assert config_path.exists()
        content = config_path.read_text()
        assert "webhooks:" in content

    @patch("feishu_webhook_bot.cli.run_ui")
    def test_main_webui_command(self, mock_run_ui):
        """Test that the 'webui' command calls run_ui with correct args."""
        exit_code = main(["webui", "-c", "my.yaml", "--host", "0.0.0.0", "--port", "9000"])
        assert exit_code == 0
        mock_run_ui.assert_called_once_with(
            config_path="my.yaml",
            host="0.0.0.0",
            port=9000,
        )

    @patch("feishu_webhook_bot.cli.FeishuWebhookClient")
    def test_main_send_command(self, mock_client_class):
        """Test that the 'send' command calls the client correctly."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client_instance

        exit_code = main(["send", "-w", "https://a.com", "-t", "Hello"])

        assert exit_code == 0
        mock_client_instance.send_text.assert_called_once_with("Hello")
