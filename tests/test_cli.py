from __future__ import annotations

from python_quick_starter import __version__
from python_quick_starter.cli import main


def test_version_string():
    assert isinstance(__version__, str)
    assert __version__


def test_default_greeting(capsys):
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Hello, world!" in captured.out


def test_named_greeting(capsys):
    exit_code = main(["--name", "Alice"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Hello, Alice!" in captured.out
