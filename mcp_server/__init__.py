"""MCP server package: exposes TravelService operations as Agent tools."""

__all__ = ["mcp", "create_server"]


def __getattr__(name: str):
    if name in ("mcp", "create_server"):
        from .server import create_server, mcp

        return mcp if name == "mcp" else create_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
