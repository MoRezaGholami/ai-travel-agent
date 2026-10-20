"""Travel subagents package — one module per specialist."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from agent.subagents.destination_agent import build_destination_agent
from agent.subagents.flight_agent import build_flight_agent
from agent.subagents.hotel_agent import build_hotel_agent


def build_travel_subagents(tools: list[BaseTool]) -> list[dict[str, Any]]:
    """Assemble declarative SubAgent specs for create_deep_agent(subagents=...)."""
    return [
        build_flight_agent(tools),
        build_hotel_agent(tools),
        build_destination_agent(tools),
    ]


__all__ = ["build_travel_subagents"]
