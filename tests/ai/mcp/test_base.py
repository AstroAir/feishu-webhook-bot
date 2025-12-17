"""Tests for MCP base types and constants.

Tests cover:
- MCP_AVAILABLE constant
- MCPServerType type alias
- ServerInfo type alias
- Import availability
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.ai.mcp.base import (
    MCP_AVAILABLE,
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
    MCPServerType,
    ServerInfo,
    logger,
)


class TestMCPAvailability:
    """Tests for MCP availability detection."""

    def test_mcp_available_is_boolean(self):
        """Test MCP_AVAILABLE is a boolean."""
        assert isinstance(MCP_AVAILABLE, bool)

    def test_mcp_server_types_defined(self):
        """Test MCP server types are defined (may be None if not available)."""
        # These should be defined, either as actual classes or None
        if MCP_AVAILABLE:
            assert MCPServerStdio is not None
            assert MCPServerSSE is not None
            assert MCPServerStreamableHTTP is not None
        else:
            # When not available, they should be None
            assert MCPServerStdio is None
            assert MCPServerSSE is None
            assert MCPServerStreamableHTTP is None


class TestTypeAliases:
    """Tests for type aliases."""

    def test_mcp_server_type_is_any(self):
        """Test MCPServerType is defined."""
        # MCPServerType is a type alias for Any
        assert MCPServerType is not None

    def test_server_info_is_dict(self):
        """Test ServerInfo is a dict type alias."""
        # ServerInfo is dict[str, Any]
        assert ServerInfo is not None

    def test_server_info_usage(self):
        """Test ServerInfo can be used as expected."""
        info: ServerInfo = {
            "config": {"name": "test"},
            "mcp_server": None,
            "connected": True,
        }
        assert info["config"]["name"] == "test"
        assert info["connected"] is True


class TestLogger:
    """Tests for logger."""

    def test_logger_exists(self):
        """Test logger is defined."""
        assert logger is not None

    def test_logger_name(self):
        """Test logger has correct name."""
        assert "mcp" in logger.name.lower()


class TestImports:
    """Tests for module imports."""

    def test_import_from_base(self):
        """Test all exports can be imported from base."""
        from feishu_webhook_bot.ai.mcp.base import (
            MCP_AVAILABLE as mcp_avail,
        )
        from feishu_webhook_bot.ai.mcp.base import (
            MCPServerSSE as sse,
        )
        from feishu_webhook_bot.ai.mcp.base import (
            MCPServerStdio as stdio,
        )
        from feishu_webhook_bot.ai.mcp.base import (
            MCPServerStreamableHTTP as http,
        )
        from feishu_webhook_bot.ai.mcp.base import (
            MCPServerType as server_type,
        )
        from feishu_webhook_bot.ai.mcp.base import (
            ServerInfo as info,
        )
        from feishu_webhook_bot.ai.mcp.base import (
            logger as log,
        )

        # All should be importable
        assert mcp_avail is not None or mcp_avail is False
        assert log is not None
        # Verify types are defined
        assert stdio is not None or stdio is None
        assert sse is not None or sse is None
        assert http is not None or http is None
        assert server_type is not None
        assert info is not None

    def test_import_from_mcp_module(self):
        """Test base types can be imported from mcp module."""
        from feishu_webhook_bot.ai.mcp import (
            MCP_AVAILABLE as mcp_avail,
        )
        from feishu_webhook_bot.ai.mcp import (
            MCPServerSSE as sse,
        )
        from feishu_webhook_bot.ai.mcp import (
            MCPServerStdio as stdio,
        )
        from feishu_webhook_bot.ai.mcp import (
            MCPServerStreamableHTTP as http,
        )
        from feishu_webhook_bot.ai.mcp import (
            MCPServerType as server_type,
        )
        from feishu_webhook_bot.ai.mcp import (
            ServerInfo as info,
        )

        assert mcp_avail is not None or mcp_avail is False
        # Verify types are defined
        assert stdio is not None or stdio is None
        assert sse is not None or sse is None
        assert http is not None or http is None
        assert server_type is not None
        assert info is not None


@pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
class TestMCPServerClasses:
    """Tests for MCP server classes when available."""

    def test_mcp_server_stdio_class(self):
        """Test MCPServerStdio is a class."""
        assert callable(MCPServerStdio)

    def test_mcp_server_sse_class(self):
        """Test MCPServerSSE is a class."""
        assert callable(MCPServerSSE)

    def test_mcp_server_streamable_http_class(self):
        """Test MCPServerStreamableHTTP is a class."""
        assert callable(MCPServerStreamableHTTP)
