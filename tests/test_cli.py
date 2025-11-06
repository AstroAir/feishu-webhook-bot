from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from feishu_webhook_bot import __version__
from feishu_webhook_bot.cli import build_parser, main


def test_version_string():
    """Test version string is valid."""
    assert isinstance(__version__, str)
    assert __version__


def test_parser_no_args():
    """Test parser shows help when no arguments provided."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.command is None


def test_parser_version_command():
    """Test version command parsing."""
    parser = build_parser()
    args = parser.parse_args(["version"])
    assert args.command == "version"


def test_parser_init_command():
    """Test init command parsing."""
    parser = build_parser()
    args = parser.parse_args(["init", "--output", "test.yaml"])
    assert args.command == "init"
    assert args.output == "test.yaml"


def test_parser_start_command():
    """Test start command parsing."""
    parser = build_parser()
    args = parser.parse_args(["start", "--config", "test.yaml"])
    assert args.command == "start"
    assert args.config == "test.yaml"


def test_parser_send_command():
    """Test send command parsing."""
    parser = build_parser()
    args = parser.parse_args(
        ["send", "--webhook", "https://example.com", "--text", "Hello"]
    )
    assert args.command == "send"
    assert args.webhook == "https://example.com"
    assert args.text == "Hello"


def test_parser_plugins_command():
    """Test plugins command parsing."""
    parser = build_parser()
    args = parser.parse_args(["plugins", "--config", "test.yaml"])
    assert args.command == "plugins"
    assert args.config == "test.yaml"


def test_version_command(capsys):
    """Test version command output."""
    exit_code = main(["version"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert __version__ in captured.out


def test_init_command():
    """Test init command creates config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"
        exit_code = main(["init", "--output", str(config_path)])
        assert exit_code == 0
        assert config_path.exists()
        
        # Verify the config file contains expected content
        content = config_path.read_text()
        assert "webhooks:" in content
        assert "scheduler:" in content
        assert "plugins:" in content
