"""Bot module - Main bot class and components.

This module provides the FeishuBot class which orchestrates all bot components.
The implementation is split into multiple submodules for better maintainability:

- base: Base class with core attributes and type definitions
- initializers/: Component initialization mixins
- lifecycle: Start/stop and signal handling
- event_handler: Incoming event processing
- messaging: Message sending utilities
"""

from __future__ import annotations

from .main import FeishuBot

__all__ = ["FeishuBot"]
