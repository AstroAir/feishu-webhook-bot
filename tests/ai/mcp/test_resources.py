"""Tests for MCP resource manager.

Tests cover:
- MCPResourceManager initialization
- Resource discovery from servers
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from feishu_webhook_bot.ai.mcp.base import ServerInfo
from feishu_webhook_bot.ai.mcp.resources import MCPResourceManager

pytestmark = pytest.mark.anyio(backends=["asyncio"])


class TestMCPResourceManagerInitialization:
    """Tests for MCPResourceManager initialization."""

    def test_create_resource_manager(self):
        """Test creating a resource manager."""
        manager = MCPResourceManager()
        assert manager is not None


class TestResourceDiscovery:
    """Tests for resource discovery functionality."""

    async def test_discover_resources_empty_servers(self):
        """Test discovering resources with no servers."""
        manager = MCPResourceManager()
        servers: dict[str, ServerInfo] = {}

        resources = await manager.discover_resources(servers)

        assert resources == []

    async def test_discover_resources_with_servers(self):
        """Test discovering resources with servers."""
        manager = MCPResourceManager()

        mock_server = MagicMock()

        servers: dict[str, ServerInfo] = {
            "test-server": {
                "config": {"name": "test-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        # Currently returns empty list as resources are discovered on first use
        resources = await manager.discover_resources(servers)

        assert isinstance(resources, list)

    async def test_discover_resources_multiple_servers(self):
        """Test discovering resources from multiple servers."""
        manager = MCPResourceManager()

        servers: dict[str, ServerInfo] = {
            "server1": {
                "config": {"name": "server1"},
                "mcp_server": MagicMock(),
                "connected": True,
            },
            "server2": {
                "config": {"name": "server2"},
                "mcp_server": MagicMock(),
                "connected": True,
            },
            "server3": {
                "config": {"name": "server3"},
                "mcp_server": MagicMock(),
                "connected": True,
            },
        }

        resources = await manager.discover_resources(servers)

        assert isinstance(resources, list)

    async def test_discover_resources_server_without_mcp_server(self):
        """Test discovering resources when server has no mcp_server."""
        manager = MCPResourceManager()

        servers: dict[str, ServerInfo] = {
            "disconnected-server": {
                "config": {"name": "disconnected-server"},
                "mcp_server": None,
                "connected": False,
            }
        }

        resources = await manager.discover_resources(servers)

        assert isinstance(resources, list)


class TestResourceManagerIntegration:
    """Integration tests for resource manager."""

    async def test_resource_discovery_lifecycle(self):
        """Test resource discovery lifecycle."""
        manager = MCPResourceManager()

        # Initially empty
        resources = await manager.discover_resources({})
        assert resources == []

        # Add servers
        servers: dict[str, ServerInfo] = {
            "server1": {
                "config": {"name": "server1"},
                "mcp_server": MagicMock(),
                "connected": True,
            }
        }

        resources = await manager.discover_resources(servers)
        assert isinstance(resources, list)

        # Remove servers
        resources = await manager.discover_resources({})
        assert resources == []
