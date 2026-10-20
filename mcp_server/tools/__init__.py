"""Register all domain MCP tools on a server instance."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import bookings, flights, hotels, knowledge


def register_all(mcp: FastMCP) -> None:
    """Attach flight, hotel, booking, and knowledge tools to the MCP server."""
    flights.register(mcp)
    hotels.register(mcp)
    bookings.register(mcp)
    knowledge.register(mcp)
