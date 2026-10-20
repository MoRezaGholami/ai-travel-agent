"""Flight specialist subagent (declarative SubAgent spec)."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from agent.subagents._common import pick_tools

SYSTEM_PROMPT = """\
You are the Flight Specialist subagent.
Your job: search and compare flights, then return a concise structured summary.

Rules:
- Use only search_flights.
- Follow the flight-search skill.
- Ask for missing origin/destination only if truly absent from the task.
- Return 2–4 options with id, airline, schedule, price, seats.
- Do NOT book anything. Do NOT invent ids or prices.
- Final message should be a short recommendation ranking for the orchestrator.
"""


def build_flight_agent(tools: list[BaseTool]) -> dict[str, Any]:
    return {
        "name": "flight-agent",
        "description": (
            "Search and compare flights. Use when the user needs flight options "
            "or cheaper/alternate flight suggestions. Pass origin, destination, "
            "optional date and max_price."
        ),
        "system_prompt": SYSTEM_PROMPT,
        "tools": pick_tools(tools, {"search_flights"}),
        # Only this agent's skill source (not orchestrator/hotel/destination skills)
        "skills": ["/skills/flight-agent/"],
    }
