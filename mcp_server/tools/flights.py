"""MCP tools for flight search."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from mcp_server.common import ok, service


def register(mcp: MCPServer) -> None:
    """Register flight-related tools on the MCP server."""

    @mcp.tool()
    def search_flights(
        origin: str | None = None,
        destination: str | None = None,
        departure_date: str | None = None,
        max_price: float | None = None,
    ) -> str:
        """Search available flights. Dates use YYYY-MM-DD. Sorted by price ascending."""
        flights = service.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            max_price=max_price,
        )
        return ok([f.to_dict() for f in flights])
