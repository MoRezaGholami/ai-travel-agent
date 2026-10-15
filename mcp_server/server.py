"""Travel MCP server (Phase 2).

Thin entrypoint: builds the MCP server, registers domain tools, runs stdio.

Tools live under mcp_server/tools/ (flights, hotels, bookings).

Run:
  python -m mcp_server
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from mcp_server.tools import register_all

mcp = MCPServer(
    "ai-travel-assistant",
    instructions=(
        "Mock travel backend tools. Use search_* to find offers, then "
        "create_booking for real reservations. Always confirm with the user "
        "before create_booking or cancel_booking. Hotel booking needs "
        "check_in and check_out (YYYY-MM-DD)."
    ),
)

register_all(mcp)


def create_server() -> MCPServer:
    """Return the configured MCP server instance."""
    return mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
