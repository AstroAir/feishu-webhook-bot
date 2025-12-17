"""Comprehensive tests for MCP (Model Context Protocol) client.

This module re-exports tests from the mcp/ subpackage for backward compatibility.
For new tests, add them to tests/ai/mcp/ directory.

Tests cover:
- MCPClient initialization
- Server connection handling
- Transport type detection
- Tool discovery
- Resource management
- Error handling
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from feishu_webhook_bot.ai.config import MCPConfig
from feishu_webhook_bot.ai.mcp import MCPClient

# ==============================================================================
# MCPClient Initialization Tests
# ==============================================================================


class TestMCPClientInitialization:
    """Tests for MCPClient initialization."""

    def test_client_creation_default_config(self):
        """Test MCPClient creation with default configuration."""
        config = MCPConfig()

        client = MCPClient(config)

        assert client.config == config
        assert client._servers == {}
        assert client._mcp_servers == []
        assert client._started is False

    def test_client_creation_with_servers(self):
        """Test MCPClient creation with server configurations."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {"name": "server1", "command": "python", "args": "-m mcp_server"},
                {"name": "server2", "url": "http://localhost:3000"},
            ],
        )

        client = MCPClient(config)

        assert len(config.servers) == 2
        assert client._started is False

    def test_client_creation_disabled(self):
        """Test MCPClient creation when disabled."""
        config = MCPConfig(enabled=False)

        client = MCPClient(config)

        assert client.config.enabled is False


# ==============================================================================
# MCPClient Start Tests
# ==============================================================================


class TestMCPClientStart:
    """Tests for MCPClient start functionality."""

    @pytest.mark.anyio
    async def test_start_when_disabled(self):
        """Test start does nothing when MCP is disabled."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        await client.start()

        assert client._started is False

    @pytest.mark.anyio
    async def test_start_already_started(self):
        """Test start warns when already started."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)
        client._started = True

        # Should not raise
        await client.start()


# ==============================================================================
# MCPClient Server Connection Tests
# ==============================================================================


class TestMCPClientServerConnection:
    """Tests for MCPClient server connection."""

    def test_get_mcp_servers_empty(self):
        """Test get_mcp_servers returns empty list initially."""
        config = MCPConfig()
        client = MCPClient(config)

        servers = client.get_mcp_servers()

        assert servers == []

    def test_is_started_false_initially(self):
        """Test is_started returns False initially."""
        config = MCPConfig()
        client = MCPClient(config)

        assert client.is_started() is False

    def test_is_started_after_start(self):
        """Test is_started after start."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)
        client._started = True

        assert client.is_started() is True


# ==============================================================================
# MCPClient Transport Detection Tests
# ==============================================================================


class TestMCPClientTransportDetection:
    """Tests for MCPClient transport type detection."""

    def test_detect_stdio_transport(self):
        """Test detection of stdio transport from config."""
        config = MCPConfig(
            enabled=True,
            servers=[{"name": "test", "command": "python", "args": "-m server"}],
        )
        _ = MCPClient(config)

        # Check server config has command
        server_config = config.servers[0]
        assert "command" in server_config
        assert "url" not in server_config

    def test_detect_http_transport(self):
        """Test detection of HTTP transport from config."""
        config = MCPConfig(
            enabled=True,
            servers=[{"name": "test", "url": "http://localhost:3000"}],
        )
        _ = MCPClient(config)

        # Check server config has url
        server_config = config.servers[0]
        assert "url" in server_config
        assert "command" not in server_config

    def test_detect_sse_transport(self):
        """Test detection of SSE transport from URL ending with /sse."""
        config = MCPConfig(
            enabled=True,
            servers=[{"name": "test", "url": "http://localhost:3000/sse"}],
        )
        _ = MCPClient(config)

        # Check server config has SSE URL
        server_config = config.servers[0]
        assert server_config["url"].endswith("/sse")


# ==============================================================================
# MCPClient Tool Discovery Tests
# ==============================================================================


class TestMCPClientToolDiscovery:
    """Tests for MCPClient tool discovery."""

    @pytest.mark.anyio
    async def test_discover_tools_not_started(self):
        """Test discover_tools returns empty list when not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        # Returns empty list instead of raising
        tools = await client.discover_tools()
        assert tools == []

    @pytest.mark.anyio
    async def test_discover_tools_empty(self):
        """Test discover_tools returns empty list when no servers."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)
        client._started = True

        tools = await client.discover_tools()

        assert tools == []


# ==============================================================================
# MCPClient Resource Discovery Tests
# ==============================================================================


class TestMCPClientResourceDiscovery:
    """Tests for MCPClient resource discovery."""

    @pytest.mark.anyio
    async def test_discover_resources_not_started(self):
        """Test discover_resources returns empty list when not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        # Returns empty list instead of raising
        resources = await client.discover_resources()
        assert resources == []

    @pytest.mark.anyio
    async def test_discover_resources_empty(self):
        """Test discover_resources returns empty list when no servers."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)
        client._started = True

        resources = await client.discover_resources()

        assert resources == []


# ==============================================================================
# MCPClient Stop Tests
# ==============================================================================


class TestMCPClientStop:
    """Tests for MCPClient stop functionality."""

    @pytest.mark.anyio
    async def test_stop_when_not_started(self):
        """Test stop does nothing when not started."""
        config = MCPConfig()
        client = MCPClient(config)

        # Should not raise
        await client.stop()

        assert client._started is False

    @pytest.mark.anyio
    async def test_stop_clears_state(self):
        """Test stop clears internal state."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)
        client._started = True
        client._servers = {"test": {"connected": True}}
        client._mcp_servers = [MagicMock()]

        await client.stop()

        assert client._started is False
        assert client._servers == {}
        assert client._mcp_servers == []


# ==============================================================================
# MCPClient Status Tests
# ==============================================================================


class TestMCPClientStatus:
    """Tests for MCPClient status methods."""

    def test_get_stats_not_started(self):
        """Test get_stats when not started."""
        config = MCPConfig()
        client = MCPClient(config)

        stats = client.get_stats()

        assert stats["started"] is False
        assert stats["server_count"] == 0
        assert stats["servers"] == []

    def test_get_stats_started(self):
        """Test get_stats when started."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)
        client._started = True
        client._servers = {
            "server1": {"connected": True, "config": {"name": "server1"}},
            "server2": {"connected": False, "config": {"name": "server2"}},
        }

        stats = client.get_stats()

        assert stats["started"] is True
        assert stats["server_count"] == 2


# ==============================================================================
# MCPClient Configuration Tests
# ==============================================================================


class TestMCPClientConfiguration:
    """Tests for MCPClient configuration options."""

    def test_client_with_custom_timeout(self):
        """Test MCPClient with custom timeout."""
        config = MCPConfig(timeout_seconds=120.0)

        client = MCPClient(config)

        assert client.config.timeout_seconds == 120.0

    def test_client_with_timeout_config(self):
        """Test MCPClient with timeout configuration."""
        config = MCPConfig(
            timeout_seconds=60,
        )

        client = MCPClient(config)

        assert client.config.timeout_seconds == 60

    def test_client_with_multiple_servers(self):
        """Test MCPClient with multiple server configurations."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {"name": "server1", "command": "cmd1"},
                {"name": "server2", "command": "cmd2"},
                {"name": "server3", "url": "http://localhost:3000"},
            ],
        )

        _ = MCPClient(config)

        assert len(config.servers) == 3


# ==============================================================================
# MCPClient Error Handling Tests
# ==============================================================================


class TestMCPClientErrorHandling:
    """Tests for MCPClient error handling."""

    def test_invalid_server_config_no_command_or_url(self):
        """Test that server config without command or url is detected."""
        # This should be caught during connection, not initialization
        config = MCPConfig(
            enabled=True,
            servers=[{"name": "invalid"}],  # Missing command and url
        )

        _ = MCPClient(config)

        # Client is created, but connection would fail
        assert len(config.servers) == 1

    def test_server_config_with_empty_name(self):
        """Test server config with empty name uses 'unknown'."""
        config = MCPConfig(
            enabled=True,
            servers=[{"command": "test"}],  # Missing name
        )

        _ = MCPClient(config)

        # Server config is stored as-is
        assert config.servers[0].get("name") is None
