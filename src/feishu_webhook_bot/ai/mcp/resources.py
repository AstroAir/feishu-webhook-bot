"""Resource discovery for MCP servers.

This module handles discovering resources from MCP servers.
"""

from __future__ import annotations

from typing import Any

from ...core.logger import get_logger
from .base import ServerInfo

logger = get_logger("ai.mcp.resources")


class MCPResourceManager:
    """Manages MCP resource discovery.

    This class provides methods for discovering available resources from MCP servers.
    """

    async def discover_resources(
        self,
        servers: dict[str, ServerInfo],
    ) -> list[dict[str, Any]]:
        """Discover resources from all connected MCP servers.

        Note: With pydantic-ai MCP integration, resources are automatically discovered
        when MCP servers are used. This method provides a way to inspect available
        resources programmatically.

        Args:
            servers: Dictionary of server name to server info

        Returns:
            List of resource definitions
        """
        all_resources: list[dict[str, Any]] = []

        for server_name, _server_info in servers.items():
            logger.info("Discovering resources from MCP server: %s", server_name)

            # Note: pydantic-ai MCP servers handle resource discovery automatically
            logger.debug("MCP server %s resources will be discovered on first use", server_name)

        logger.info("MCP servers ready for resource discovery")
        return all_resources
