"""Hotel specialist subagent (declarative SubAgent spec)."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from agent.subagents._common import pick_tools

SYSTEM_PROMPT = """\
You are the Hotel Specialist subagent.
Your job: search and compare hotels for given stay dates, then summarize.

Rules:
- Use only search_hotels.
- Follow the hotel-search skill.
- check_in and check_out (YYYY-MM-DD) are required; if missing, say what is needed.
- Return 2–4 options with id, name, stars, nightly price, total_price, rooms.
- Do NOT book anything. Do NOT invent ids or prices.
- Final message should be a short recommendation ranking for the orchestrator.
"""


def build_hotel_agent(tools: list[BaseTool]) -> dict[str, Any]:
    return {
        "name": "hotel-agent",
        "description": (
            "Search and compare hotels. Use when the user needs lodging options. "
            "Pass city, check_in, check_out, optional rooms/budget/stars."
        ),
        "system_prompt": SYSTEM_PROMPT,
        "tools": pick_tools(tools, {"search_hotels"}),
        "skills": ["/skills/hotel-agent/"],
    }
