"""Load travel tools from the MCP server (no duplicate tool logic).

Single source of tool implementations: mcp_server/tools/*
This module only connects the Deep Agent to that MCP server over stdio.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from langchain_core.tools import BaseTool

PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def _aload_travel_mcp_tools() -> list[BaseTool]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "travel": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "mcp_server"],
                "cwd": str(PROJECT_ROOT),
                # Inherit env so the child process sees the same project setup
                "env": {k: v for k, v in os.environ.items() if v is not None},
            }
        }
    )
    return await client.get_tools()


def load_travel_mcp_tools() -> list[BaseTool]:
    """Sync helper used by orchestrator startup."""
    return asyncio.run(_aload_travel_mcp_tools())
