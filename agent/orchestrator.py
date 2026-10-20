"""Travel Deep Agent — main orchestrator.

Tools come from MCP (mcp_server).
Conversation memory: SQLite checkpointer + thread_id.
Specialized work: flight / hotel / destination subagents.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from agent.mcp_tools import load_travel_mcp_tools
from agent.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from agent.subagents import build_travel_subagents

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DB = PROJECT_ROOT / "data" / "checkpoints.sqlite"


def _load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=True)


def _build_model():
    """Build chat model from .env (supports custom gateway via LLM_BASE_URL)."""
    _load_env()

    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("API_KEY")
    )
    base_url = (
        os.getenv("LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
    )
    model_id = os.getenv("TRAVEL_AGENT_MODEL", "openai/gpt-4o")

    if not api_key:
        raise RuntimeError(
            "No API key in .env. Set OPENAI_API_KEY or LLM_API_KEY. See .env.example"
        )

    if base_url or model_id.startswith(("openai/", "openai:", "google/", "anthropic/")):
        from langchain_openai import ChatOpenAI

        model_name = model_id
        if model_id.startswith("openai:") and "/" not in model_id:
            model_name = "openai/" + model_id.split(":", 1)[1]
        kwargs: dict = {"model": model_name, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url.rstrip("/")
        return ChatOpenAI(**kwargs)

    os.environ.setdefault("OPENAI_API_KEY", api_key)
    return model_id


def _build_checkpointer():
    """Persistent conversation memory across turns (and CLI restarts)."""
    from langgraph.checkpoint.sqlite import SqliteSaver

    CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return checkpointer


def create_travel_orchestrator():
    """Build Deep Agent with MCP tools, subagents, skills, and thread memory."""
    _load_env()

    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend

    model = _build_model()
    tools = load_travel_mcp_tools()
    subagents = build_travel_subagents(tools)
    backend = FilesystemBackend(root_dir=PROJECT_ROOT)
    checkpointer = _build_checkpointer()

    # Booking stays on the orchestrator (with human confirmation)
    interrupt_on = {
        "create_booking": True,
        "cancel_booking": True,
    }

    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        subagents=subagents,
        # Orchestrator-only skills (trip planning + booking). Specialists have their own.
        skills=["/skills/orchestrator/"],
        backend=backend,
        interrupt_on=interrupt_on,
        checkpointer=checkpointer,
        name="travel-orchestrator",
    )
    return agent
