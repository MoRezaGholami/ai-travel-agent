"""Register all domain MCP tools on a server instance."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import bookings, flights, hotels


def register_all(mcp: MCPServer) -> None:
    """Attach flight, hotel, and booking tools to the given MCP server."""
    flights.register(mcp)
    hotels.register(mcp)
    bookings.register(mcp)
