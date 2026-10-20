"""Itinerary specialist — builds a simple day-by-day plan from RAG knowledge."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from agent.subagents._common import pick_tools

SYSTEM_PROMPT = """\
You are the Itinerary Specialist subagent.
Your job: build a practical day-by-day sightseeing plan using destination knowledge.

Rules:
- Use only search_knowledge (multiple queries OK: attractions, neighborhoods, transport).
- Follow the itinerary-builder skill.
- Output a clear day-by-day plan (Day 1, Day 2, ...) with morning/afternoon suggestions.
- Keep it realistic (travel time, clustering nearby sights).
- Do NOT search flights/hotels or create bookings.
- Summarize in English for the orchestrator; cite knowledge sources when useful.
"""


def build_itinerary_agent(tools: list[BaseTool]) -> dict[str, Any]:
    return {
        "name": "itinerary-agent",
        "description": (
            "Build a day-by-day sightseeing itinerary from the knowledge base. "
            "Pass city, number of days, and optional interests (history, food, nightlife)."
        ),
        "system_prompt": SYSTEM_PROMPT,
        "tools": pick_tools(tools, {"search_knowledge"}),
        "skills": ["/skills/itinerary-agent/"],
    }
