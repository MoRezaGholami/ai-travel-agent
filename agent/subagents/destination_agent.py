"""Destination guide subagent (RAG) — declarative SubAgent spec.

Decision path: orchestrator ``task(destination-agent)`` → only tool
``search_knowledge`` → ``rag.retriever`` BM25. Orchestrator never calls RAG itself.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from agent.subagents._common import pick_tools

SYSTEM_PROMPT = """\
You are the Destination Guide subagent.
Your job: retrieve destination knowledge (attractions, neighborhoods, transport, tips).

Rules:
- Use only search_knowledge.
- Follow the destination-guide skill.
- Prefer knowledge-base content; summarize clearly in English for the orchestrator.
- Cite source/heading when useful.
- Do NOT search flights/hotels or create bookings.
"""


def build_destination_agent(tools: list[BaseTool]) -> dict[str, Any]:
    return {
        "name": "destination-agent",
        "description": (
            "Retrieve destination guide info via RAG: attractions, neighborhoods, "
            "transport, culture tips. Pass a query and optional city "
            "(istanbul/dubai)."
        ),
        "system_prompt": SYSTEM_PROMPT,
        "tools": pick_tools(tools, {"search_knowledge"}),
        "skills": ["/skills/destination-agent/"],
    }
