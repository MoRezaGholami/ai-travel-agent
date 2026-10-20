"""MCP tools for hotel search."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.common import ok, service


def register(mcp: FastMCP) -> None:
    """Register hotel-related tools on the MCP server."""

    @mcp.tool()
    def search_hotels(
        city: str,
        check_in: str,
        check_out: str,
        rooms: int = 1,
        max_price_per_night: float | None = None,
        min_stars: int | None = None,
    ) -> str:
        """Search hotels for a stay. check_in/check_out are YYYY-MM-DD. total_price includes nights*rooms."""
        hotels = service.search_hotels(
            city=city,
            check_in=check_in,
            check_out=check_out,
            rooms=rooms,
            max_price_per_night=max_price_per_night,
            min_stars=min_stars,
        )
        return ok([h.to_dict() for h in hotels])
