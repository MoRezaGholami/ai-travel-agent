"""Shared turn runner for CLI and FastAPI (HITL-aware)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Literal

from langgraph.types import Command

Status = Literal["ok", "needs_approval", "error"]


@dataclass
class PendingAction:
    """One tool call waiting for human approval."""

    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "args": self.args,
            "description": self.description,
        }


@dataclass
class TurnResult:
    thread_id: str
    status: Status
    reply: str | None = None
    pending: list[PendingAction] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "status": self.status,
            "reply": self.reply,
            "pending": [p.to_dict() for p in self.pending],
            "error": self.error,
        }


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def pending_interrupts(agent, thread_id: str) -> tuple:
    state = agent.get_state(_config(thread_id))
    return getattr(state, "interrupts", None) or ()


def parse_pending(intr) -> list[PendingAction]:
    value = getattr(intr, "value", intr)
    if not isinstance(value, dict):
        return [PendingAction(tool="unknown", description=str(value))]

    requests = value.get("action_requests") or []
    if requests:
        out: list[PendingAction] = []
        for req in requests:
            out.append(
                PendingAction(
                    tool=str(req.get("name") or "?"),
                    args=dict(req.get("args") or {}),
                    description=req.get("description"),
                )
            )
        return out

    if value.get("type") == "tool_approval":
        return [
            PendingAction(
                tool=str(value.get("name") or "?"),
                args=dict(value.get("args") or {}),
                description=value.get("description"),
            )
        ]

    return [PendingAction(tool="unknown", description=json.dumps(value, ensure_ascii=False))]


def _resume_value(intr, decision: dict[str, Any]) -> Any:
    value = getattr(intr, "value", intr)
    if isinstance(value, dict) and value.get("action_requests"):
        n = len(value["action_requests"])
        return {"decisions": [decision] * n}
    return decision


def _run_stream(agent, payload, thread_id: str) -> tuple[str | None, bool]:
    """Stream one graph run; return (final_ai_text, hit_interrupt)."""
    config = _config(thread_id)
    final_text: str | None = None
    hit_interrupt = False

    for chunk in agent.stream(payload, config=config, stream_mode="updates"):
        if not isinstance(chunk, dict):
            continue
        for node, update in chunk.items():
            if node == "__interrupt__":
                hit_interrupt = True
                continue
            if not isinstance(update, dict):
                continue
            for msg in update.get("messages") or []:
                content = getattr(msg, "content", None)
                tool_calls = getattr(msg, "tool_calls", None)
                if content and not tool_calls and getattr(msg, "type", "") == "ai":
                    final_text = content if isinstance(content, str) else str(content)

    return final_text, hit_interrupt


def _fallback_reply(agent, thread_id: str) -> str | None:
    state = agent.get_state(_config(thread_id))
    values = getattr(state, "values", None) or {}
    messages = values.get("messages") or []
    if not messages:
        return None
    last = messages[-1]
    content = getattr(last, "content", None)
    return content if isinstance(content, str) else (str(content) if content else None)


def _result_after_run(agent, thread_id: str, final: str | None, hit_interrupt: bool) -> TurnResult:
    pending_raw = pending_interrupts(agent, thread_id)
    if hit_interrupt or pending_raw:
        actions: list[PendingAction] = []
        for intr in pending_raw:
            actions.extend(parse_pending(intr))
        return TurnResult(
            thread_id=thread_id,
            status="needs_approval",
            reply=final,
            pending=actions,
        )

    reply = final or _fallback_reply(agent, thread_id)
    return TurnResult(thread_id=thread_id, status="ok", reply=reply)


def chat(agent, thread_id: str, message: str) -> TurnResult:
    """Send a user message. If an interrupt is already pending, refuse chat until approve/reject."""
    pending = pending_interrupts(agent, thread_id)
    if pending:
        actions: list[PendingAction] = []
        for intr in pending:
            actions.extend(parse_pending(intr))
        return TurnResult(
            thread_id=thread_id,
            status="needs_approval",
            reply="An action is waiting for approval. Call /v1/approve or /v1/reject first.",
            pending=actions,
        )

    try:
        final, hit = _run_stream(
            agent,
            {"messages": [{"role": "user", "content": message}]},
            thread_id,
        )
        return _result_after_run(agent, thread_id, final, hit)
    except Exception as exc:  # noqa: BLE001
        return TurnResult(
            thread_id=thread_id,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def approve(
    agent,
    thread_id: str,
    *,
    decision: Literal["approve", "reject"] = "approve",
    reason: str | None = None,
) -> TurnResult:
    """Resume a pending interrupt with approve or reject."""
    pending = pending_interrupts(agent, thread_id)
    if not pending:
        return TurnResult(
            thread_id=thread_id,
            status="error",
            error="No pending action to approve/reject for this thread_id.",
        )

    if decision == "approve":
        payload_decision: dict[str, Any] = {"type": "approve"}
    else:
        payload_decision = {
            "type": "reject",
            "message": reason or "User rejected the action.",
        }

    try:
        resume = Command(resume=_resume_value(pending[0], payload_decision))
        final, hit = _run_stream(agent, resume, thread_id)
        return _result_after_run(agent, thread_id, final, hit)
    except Exception as exc:  # noqa: BLE001
        return TurnResult(
            thread_id=thread_id,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def get_pending(agent, thread_id: str) -> TurnResult:
    pending = pending_interrupts(agent, thread_id)
    if not pending:
        return TurnResult(thread_id=thread_id, status="ok", reply=None, pending=[])
    actions: list[PendingAction] = []
    for intr in pending:
        actions.extend(parse_pending(intr))
    return TurnResult(
        thread_id=thread_id,
        status="needs_approval",
        pending=actions,
    )


def _message_text(content: object) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif hasattr(block, "get"):
                parts.append(str(block.get("text") or ""))
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


def serialize_chat_messages(messages: list[Any]) -> list[dict[str, str]]:
    """Keep user + assistant text turns for the UI (skip tool-only steps)."""
    out: list[dict[str, str]] = []
    for msg in messages:
        msg_type = getattr(msg, "type", "")
        content = _message_text(getattr(msg, "content", None))
        tool_calls = getattr(msg, "tool_calls", None) or []
        if msg_type == "human" and content:
            out.append({"role": "user", "content": content})
        elif msg_type == "ai" and content and not tool_calls:
            out.append({"role": "assistant", "content": content})
    return out


def list_thread_ids(*, limit: int = 40) -> list[str]:
    """Distinct conversation threads from the SQLite checkpointer, newest first."""
    from agent.orchestrator import CHECKPOINT_DB

    if not CHECKPOINT_DB.exists():
        return []

    with sqlite3.connect(str(CHECKPOINT_DB)) as conn:
        rows = conn.execute(
            """
            SELECT thread_id
            FROM checkpoints
            WHERE thread_id IS NOT NULL
              AND length(thread_id) >= 8
              AND thread_id NOT IN ('string', 'None', 'null')
            GROUP BY thread_id
            ORDER BY MAX(checkpoint_id) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [r[0] for r in rows]


def list_threads(agent, *, limit: int = 40) -> list[dict[str, Any]]:
    """Thread summaries for the chat sidebar."""
    items: list[dict[str, Any]] = []
    for thread_id in list_thread_ids(limit=limit):
        try:
            state = agent.get_state(_config(thread_id))
        except Exception:  # noqa: BLE001
            continue
        values = getattr(state, "values", None) or {}
        messages = values.get("messages") or []
        chat_msgs = serialize_chat_messages(messages)
        if not chat_msgs:
            continue
        title = next((m["content"] for m in chat_msgs if m["role"] == "user"), "Chat")
        title = " ".join(title.split())
        if len(title) > 48:
            title = title[:45] + "..."
        pending = bool(getattr(state, "interrupts", None))
        items.append(
            {
                "thread_id": thread_id,
                "title": title,
                "preview": chat_msgs[-1]["content"][:80],
                "message_count": len(chat_msgs),
                "needs_approval": pending,
            }
        )
    return items


def get_thread_history(agent, thread_id: str) -> dict[str, Any]:
    """Full UI-visible history + pending approval for one thread."""
    state = agent.get_state(_config(thread_id))
    values = getattr(state, "values", None) or {}
    messages = serialize_chat_messages(values.get("messages") or [])
    pending_raw = getattr(state, "interrupts", None) or ()
    actions: list[PendingAction] = []
    for intr in pending_raw:
        actions.extend(parse_pending(intr))
    return {
        "thread_id": thread_id,
        "messages": messages,
        "status": "needs_approval" if actions else "ok",
        "pending": [p.to_dict() for p in actions],
    }
