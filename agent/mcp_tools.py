"""Load travel tools from the MCP server (no duplicate tool logic).

Single source of tool implementations: mcp_server/tools/*
This module only connects the Deep Agent to that MCP server over stdio.

MCP adapter tools are async-only; Deep Agent's ToolNode calls them sync,
so we wrap each tool with a sync bridge.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import sys
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_async(coro):
    """Run a coroutine from sync code (works inside or outside an event loop)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Already inside a loop (e.g. Jupyter / nested async) — run in a worker thread.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _as_sync_tool(tool: BaseTool) -> BaseTool:
    """Ensure StructuredTool has a sync func; MCP adapters only set coroutine."""
    if not isinstance(tool, StructuredTool):
        return tool
    if tool.func is not None:
        return tool
    if tool.coroutine is None:
        return tool

    coroutine = tool.coroutine

    async def _acall(*args: Any, **kwargs: Any) -> Any:
        return await coroutine(*args, **kwargs)

    def _call(*args: Any, **kwargs: Any) -> Any:
        return _run_async(coroutine(*args, **kwargs))

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        func=_call,
        coroutine=_acall,
        response_format=getattr(tool, "response_format", "content"),
        metadata=getattr(tool, "metadata", None),
        tags=getattr(tool, "tags", None),
    )


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
    tools = await client.get_tools()
    return [_as_sync_tool(t) for t in tools]


def load_travel_mcp_tools() -> list[BaseTool]:
    """Sync helper used by orchestrator startup (works inside FastAPI's event loop)."""
    return _run_async(_aload_travel_mcp_tools())
