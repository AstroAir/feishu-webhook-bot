"""Top-level package for python-quick-starter.

This package provides a minimal CLI and structure for starting new Python projects.
"""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:  # pragma: no cover - best-effort during development
    __version__ = version("python-quick-starter")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
