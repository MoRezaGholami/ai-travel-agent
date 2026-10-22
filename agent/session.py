"""Shared turn runner for CLI and FastAPI (HITL-aware).

## HITL / pending-approval contract

Scoped by ``thread_id`` (SqliteSaver). Threads never share interrupts.

1. **What pauses**
   ``booking-agent`` sets ``interrupt_on`` for ``create_booking`` / ``cancel_booking``.
   The graph parks with one or more ``action_requests`` until approve/reject.

2. **Multiple pending actions in one pause**
   One interrupt may list N ``action_requests`` (e.g. two tool calls).
   Approve/reject is **all-or-nothing**: the same decision is applied to every
   request in that interrupt (see ``_resume_value``). The API returns the full
   ``pending`` list so the UI can show every action before the user decides.
   Per-action mixed approve/reject is intentionally out of scope for this app
   (booking flow is one sensitive action at a time in practice).

3. **Duplicate approve/reject**
   Idempotent: if nothing is pending, return ``status=ok`` with a clear reply
   (not an error). Clients may safely retry.

4. **Concurrent threads**
   Checkpointer isolates state per ``thread_id``. The FastAPI layer also holds a
   process-wide lock around graph runs so SQLite checkpoints stay consistent
   when several threads are active.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Literal

from langgraph.types import Command

Status = Literal["ok", "needs_approval", "error"]

_NO_PENDING_REPLY = "No pending action for this thread (already resolved or never interrupted)."


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
    """Map one human decision onto every action_request in this interrupt."""
    value = getattr(intr, "value", intr)
    if isinstance(value, dict) and value.get("action_requests"):
        n = len(value["action_requests"])
        return {"decisions": [decision] * n}
    return decision


def _decision_payload(
    decision: Literal["approve", "reject"],
    reason: str | None = None,
) -> dict[str, Any]:
    if decision == "approve":
        return {"type": "approve"}
    return {
        "type": "reject",
        "message": reason or "User rejected the action.",
    }


def _collect_pending_actions(agent, thread_id: str) -> list[PendingAction]:
    actions: list[PendingAction] = []
    for intr in pending_interrupts(agent, thread_id):
        actions.extend(parse_pending(intr))
    return actions


def _resume_with_decision(
    agent,
    thread_id: str,
    payload_decision: dict[str, Any],
) -> tuple[str | None, bool]:
    """Resume the current interrupt (all its action_requests get the same decision).

    If the graph pauses again afterward, callers return ``needs_approval`` so the
    human reviews the next batch — we never auto-approve newly created interrupts.
    """
    pending = pending_interrupts(agent, thread_id)
    if not pending:
        return None, False
    resume = Command(resume=_resume_value(pending[0], payload_decision))
    return _run_stream(agent, resume, thread_id)


_SUBAGENT_STATUS: dict[str, str] = {
    "flight-agent": "Flight agent searching…",
    "hotel-agent": "Hotel agent searching…",
    "destination-agent": "Destination guide researching…",
    "itinerary-agent": "Itinerary agent planning…",
    "booking-agent": "Booking agent working…",
}

_NODE_STATUS: dict[str, str] = {
    "model": "Orchestrator thinking…",
    "tools": "Running tools…",
}


def _status_for_node(node: str) -> str | None:
    if node in _NODE_STATUS:
        return _NODE_STATUS[node]
    if "SkillsMiddleware" in node:
        return "Loading skills…"
    if node.startswith("_") or "Middleware" in node or "PatchTool" in node:
        return None
    if node == "__interrupt__":
        return "Waiting for your approval…"
    return f"Working ({node})…"


def _tool_call_name_args(tc: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(tc, dict):
        return str(tc.get("name") or "?"), dict(tc.get("args") or {})
    return str(getattr(tc, "name", None) or "?"), dict(getattr(tc, "args", None) or {})


def _chunk_text(content: object) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return str(content)


def iter_run_events(agent, payload, thread_id: str):
    """Yield live status / token / reply events, then leave finalization to caller helpers."""
    config = _config(thread_id)
    final_text: str | None = None
    hit_interrupt = False
    seen_status: str | None = None

    def emit_status(label: str):
        nonlocal seen_status
        if label and label != seen_status:
            seen_status = label
            return {"type": "status", "label": label}
        return None

    yield {"type": "meta", "thread_id": thread_id}
    start = emit_status("Starting…")
    if start:
        yield start

    for item in agent.stream(
        payload,
        config=config,
        stream_mode=["updates", "messages"],
    ):
        mode, chunk = item if isinstance(item, tuple) and len(item) == 2 else ("updates", item)

        if mode == "messages":
            msg = chunk[0] if isinstance(chunk, tuple) else chunk
            tool_chunks = getattr(msg, "tool_call_chunks", None) or []
            if tool_chunks:
                continue
            text = _chunk_text(getattr(msg, "content", None))
            if text:
                evt = emit_status("Writing reply…")
                if evt:
                    yield evt
                yield {"type": "token", "text": text}
            continue

        if not isinstance(chunk, dict):
            continue

        for node, update in chunk.items():
            if node == "__interrupt__":
                hit_interrupt = True
                evt = emit_status("Waiting for your approval…")
                if evt:
                    yield evt
                continue

            evt = emit_status(_status_for_node(node) or "")
            if evt:
                yield evt

            if not isinstance(update, dict):
                continue

            for msg in update.get("messages") or []:
                msg_type = getattr(msg, "type", "")
                tool_calls = getattr(msg, "tool_calls", None) or []
                content = getattr(msg, "content", None)
                name = getattr(msg, "name", None)

                if tool_calls:
                    for tc in tool_calls:
                        tc_name, tc_args = _tool_call_name_args(tc)
                        if tc_name == "task":
                            sub = str(tc_args.get("subagent_type") or "")
                            label = _SUBAGENT_STATUS.get(
                                sub, f"Delegating to {sub or 'specialist'}…"
                            )
                            evt = emit_status(label)
                            if evt:
                                yield evt
                        else:
                            evt = emit_status(f"Calling {tc_name}…")
                            if evt:
                                yield evt
                    continue

                if msg_type == "tool":
                    if name == "task":
                        evt = emit_status("Specialist finished — synthesizing…")
                        if evt:
                            yield evt
                    else:
                        evt = emit_status(f"Got result from {name or 'tool'}…")
                        if evt:
                            yield evt
                    continue

                if content and msg_type == "ai" and not tool_calls:
                    text = content if isinstance(content, str) else str(content)
                    final_text = text
                    yield {"type": "reply_partial", "text": text}

    yield {
        "type": "_internal_finish",
        "final_text": final_text,
        "hit_interrupt": hit_interrupt,
    }


def _run_stream(agent, payload, thread_id: str) -> tuple[str | None, bool]:
    """Stream one graph run; return (final_ai_text, hit_interrupt)."""
    final_text: str | None = None
    hit_interrupt = False
    for event in iter_run_events(agent, payload, thread_id):
        if event.get("type") == "_internal_finish":
            final_text = event.get("final_text")
            hit_interrupt = bool(event.get("hit_interrupt"))
    return final_text, hit_interrupt


def iter_chat_events(agent, thread_id: str, message: str):
    """SSE-friendly events for one user chat turn."""
    actions = _collect_pending_actions(agent, thread_id)
    if actions:
        yield {
            "type": "done",
            **TurnResult(
                thread_id=thread_id,
                status="needs_approval",
                reply=(
                    "An action is waiting for approval. "
                    "Call /v1/approve or /v1/reject first."
                ),
                pending=actions,
            ).to_dict(),
        }
        return

    try:
        final_text: str | None = None
        hit_interrupt = False
        for event in iter_run_events(
            agent,
            {"messages": [{"role": "user", "content": message}]},
            thread_id,
        ):
            if event.get("type") == "_internal_finish":
                final_text = event.get("final_text")
                hit_interrupt = bool(event.get("hit_interrupt"))
                continue
            yield event
        result = _result_after_run(agent, thread_id, final_text, hit_interrupt)
        yield {"type": "done", **result.to_dict()}
    except Exception as exc:  # noqa: BLE001
        yield {
            "type": "done",
            **TurnResult(
                thread_id=thread_id,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            ).to_dict(),
        }


def iter_approve_events(
    agent,
    thread_id: str,
    *,
    decision: Literal["approve", "reject"] = "approve",
    reason: str | None = None,
):
    """SSE-friendly events for approve/reject resume (idempotent if nothing pending)."""
    pending = pending_interrupts(agent, thread_id)
    if not pending:
        yield {
            "type": "done",
            **TurnResult(
                thread_id=thread_id,
                status="ok",
                reply=_NO_PENDING_REPLY,
                pending=[],
            ).to_dict(),
        }
        return

    payload_decision = _decision_payload(decision, reason)
    try:
        resume = Command(resume=_resume_value(pending[0], payload_decision))
        final_text: str | None = None
        hit_interrupt = False
        for event in iter_run_events(agent, resume, thread_id):
            if event.get("type") == "_internal_finish":
                final_text = event.get("final_text")
                hit_interrupt = bool(event.get("hit_interrupt"))
                continue
            yield event
        result = _result_after_run(agent, thread_id, final_text, hit_interrupt)
        yield {"type": "done", **result.to_dict()}
    except Exception as exc:  # noqa: BLE001
        yield {
            "type": "done",
            **TurnResult(
                thread_id=thread_id,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            ).to_dict(),
        }


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
    actions = _collect_pending_actions(agent, thread_id)
    if actions:
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
    """Resume a pending interrupt with approve or reject.

    Idempotent when nothing is pending. Multiple ``action_requests`` in the same
    interrupt all receive this decision (all-or-nothing).
    """
    if not pending_interrupts(agent, thread_id):
        return TurnResult(
            thread_id=thread_id,
            status="ok",
            reply=_NO_PENDING_REPLY,
            pending=[],
        )

    try:
        final, hit = _resume_with_decision(
            agent, thread_id, _decision_payload(decision, reason)
        )
        return _result_after_run(agent, thread_id, final, hit)
    except Exception as exc:  # noqa: BLE001
        return TurnResult(
            thread_id=thread_id,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def get_pending(agent, thread_id: str) -> TurnResult:
    actions = _collect_pending_actions(agent, thread_id)
    if not actions:
        return TurnResult(thread_id=thread_id, status="ok", reply=None, pending=[])
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
