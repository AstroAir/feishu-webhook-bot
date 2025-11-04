from __future__ import annotations

from feishu_webhook_bot import __version__
from feishu_webhook_bot.cli import main


def test_version_string():
    assert isinstance(__version__, str)
    assert __version__


def test_default_greeting(capsys):
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Hello from Feishu Webhook Bot, world!" in captured.out


def test_named_greeting(capsys):
    exit_code = main(["--name", "Alice"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Hello from Feishu Webhook Bot, Alice!" in captured.out
