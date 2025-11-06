"""Plugin system for extensible bot functionality.

This package provides:
- Base plugin class
- Plugin manager with discovery and loading
- Hot-reload support via file watching
"""

from .base import BasePlugin, PluginMetadata
from .manager import PluginManager

__all__ = ["BasePlugin", "PluginMetadata", "PluginManager"]
