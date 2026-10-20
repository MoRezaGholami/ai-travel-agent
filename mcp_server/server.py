"""Travel MCP server (Phase 2).

Thin entrypoint: builds the MCP server, registers domain tools, runs stdio.

Tools live under mcp_server/tools/ (flights, hotels, bookings).

Run:
  python -m mcp_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.tools import register_all

mcp = FastMCP(
    "ai-travel-assistant",
    instructions=(
        "Mock travel backend tools. Use search_* for offers, then create_booking "
        "only after user confirmation. Use cancel_booking to cancel. "
        "Hotel booking requires check_in and check_out as YYYY-MM-DD."
    ),
)

register_all(mcp)


def create_server() -> FastMCP:
    """Return the configured MCP server instance."""
    return mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
