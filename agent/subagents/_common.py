"""Shared helpers for subagent specs."""

from __future__ import annotations

from langchain_core.tools import BaseTool


def pick_tools(tools: list[BaseTool], names: set[str]) -> list[BaseTool]:
    return [t for t in tools if getattr(t, "name", None) in names]
