"""Shared helpers for MCP tool modules."""

from __future__ import annotations

import json
from typing import Any

from backend import TravelService

# One shared backend → same SQLite file as Phase 1 CLI (data/travel.db)
service = TravelService()


def ok(data: Any) -> str:
    """Serialize tool results as JSON text for the MCP client."""
    return json.dumps(data, ensure_ascii=False, indent=2)
