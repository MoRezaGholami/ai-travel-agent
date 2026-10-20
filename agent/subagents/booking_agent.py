"""Booking specialist subagent — create/cancel/status with confirmation rules."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from agent.subagents._common import pick_tools

SYSTEM_PROMPT = """\
You are the Booking Specialist subagent.
Your job: create, cancel, and inspect bookings using real MCP booking tools.

Rules:
- Follow the booking-management skill strictly.
- For create_booking / cancel_booking: the orchestrator must already have user intent.
  Still restate the action and price/id before calling the tool when possible.
- Never invent booking ids, prices, or item ids.
- Prefer get_booking / list_bookings for status questions.
- Return a short structured result for the orchestrator (id, status, total_price, details).
"""


def build_booking_agent(tools: list[BaseTool]) -> dict[str, Any]:
    return {
        "name": "booking-agent",
        "description": (
            "Create, cancel, or check real bookings. Use after the user confirms a "
            "specific flight/hotel (or asks to cancel/status). Pass booking_type, "
            "item_id, user_name, and hotel dates/rooms when needed."
        ),
        "system_prompt": SYSTEM_PROMPT,
        "tools": pick_tools(
            tools,
            {
                "create_booking",
                "cancel_booking",
                "get_booking",
                "list_bookings",
            },
        ),
        "skills": ["/skills/booking-agent/"],
        # Human-in-the-loop for sensitive side effects
        "interrupt_on": {
            "create_booking": True,
            "cancel_booking": True,
        },
    }
