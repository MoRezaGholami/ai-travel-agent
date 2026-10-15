"""MCP tools for create / cancel / status / list bookings."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from mcp_server.common import ok, service


def register(mcp: MCPServer) -> None:
    """Register booking-related tools on the MCP server."""

    @mcp.tool()
    def create_booking(
        booking_type: str,
        item_id: str,
        user_name: str,
        check_in: str | None = None,
        check_out: str | None = None,
        rooms: int = 1,
    ) -> str:
        """Create a REAL booking in SQLite. booking_type is 'flight' or 'hotel'.
        For hotels, check_in and check_out are required. Decreases inventory.
        """
        booking = service.create_booking(
            booking_type=booking_type,
            item_id=item_id,
            user_name=user_name,
            check_in=check_in,
            check_out=check_out,
            rooms=rooms,
        )
        return ok(booking.to_dict())

    @mcp.tool()
    def cancel_booking(booking_id: str) -> str:
        """Cancel a confirmed booking and restore inventory. Requires a real booking id."""
        booking = service.cancel_booking(booking_id)
        return ok(booking.to_dict())

    @mcp.tool()
    def get_booking(booking_id: str) -> str:
        """Get booking status and details by booking id (e.g. BK-XXXXXXXX)."""
        booking = service.get_booking(booking_id)
        return ok(booking.to_dict())

    @mcp.tool()
    def list_bookings(user_name: str | None = None) -> str:
        """List bookings. Optionally filter by user_name."""
        bookings = service.list_bookings(user_name=user_name)
        return ok([b.to_dict() for b in bookings])
