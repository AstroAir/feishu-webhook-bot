"""Test configuration hooks."""

import httpx
import pytest


if not hasattr(pytest, "httpx"):
	class _PytestHttpxNamespace:
		HTTPStatusError = httpx.HTTPStatusError

	setattr(pytest, "httpx", _PytestHttpxNamespace())
