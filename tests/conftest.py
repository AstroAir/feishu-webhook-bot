"""Test configuration hooks."""

from pathlib import Path

import httpx
import pytest


# Configure anyio to only use asyncio backend (skip trio tests)
@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio to use only asyncio backend."""
    return "asyncio"


if not hasattr(pytest, "httpx"):

    class _PytestHttpxNamespace:
        HTTPStatusError = httpx.HTTPStatusError

    pytest.httpx = _PytestHttpxNamespace()


@pytest.fixture
def fixtures_dir():
    """Get the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def mocks_dir():
    """Get the mocks directory path."""
    return Path(__file__).parent / "mocks"
