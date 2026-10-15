"""MCP tool for RAG knowledge search (Persian + English queries)."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from mcp_server.common import ok


def register(mcp: MCPServer) -> None:
    """Register knowledge/RAG tools on the MCP server."""

    @mcp.tool()
    def search_knowledge(
        query: str,
        city: str | None = None,
        top_k: int = 4,
    ) -> str:
        """Search the Persian travel knowledge base (جاذبه‌ها، محله‌ها، حمل‌ونقل، نکات).

        Prefer Persian queries. Optional city filter: استانبول/دبی or istanbul/dubai.
        Use for static destination info — NOT live flight/hotel prices or bookings.
        """
        from rag import search_knowledge as _search

        hits = _search(query=query, city=city, top_k=top_k)
        return ok(hits)
