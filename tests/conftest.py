"""Test configuration hooks."""

from pathlib import Path

import httpx
import pytest


if not hasattr(pytest, "httpx"):
	class _PytestHttpxNamespace:
		HTTPStatusError = httpx.HTTPStatusError

	setattr(pytest, "httpx", _PytestHttpxNamespace())


@pytest.fixture
def fixtures_dir():
	"""Get the fixtures directory path."""
	return Path(__file__).parent / "fixtures"


@pytest.fixture
def mocks_dir():
	"""Get the mocks directory path."""
	return Path(__file__).parent / "mocks"
