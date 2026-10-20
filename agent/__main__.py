"""Interactive CLI for the travel orchestrator.

Run:
  .\\.venv\\Scripts\\python.exe -m agent

Conversation memory:
  - Same process keeps one thread_id (multi-turn edits work).
  - State is stored in data/checkpoints.sqlite
  - Optional: --thread <id> to resume a previous chat

Booking create/cancel pauses for your approval (HITL interrupt).
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from typing import Any


def _preview(text: object, limit: int = 160) -> str:
    s = str(text or "").replace("\n", " ").strip()
    if len(s) > limit:
        return s[: limit - 3] + "..."
    return s


def _print_message(msg, *, prefix: str = "  ") -> None:
    """Print a short line for one LangChain message (AI / tool / human)."""
    msg_type = getattr(msg, "type", type(msg).__name__)
    name = getattr(msg, "name", None) or msg_type
    content = getattr(msg, "content", "")
    tool_calls = getattr(msg, "tool_calls", None) or []

    if tool_calls:
        for tc in tool_calls:
            tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "?")
            tc_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
            # ASCII only — Windows CMD (cp1252) cannot print arrows
            print(f"{prefix}-> tool {tc_name}({_preview(tc_args, 100)})", flush=True)
        return

    if msg_type == "tool":
        print(f"{prefix}<- {name}: {_preview(content)}", flush=True)
        return

    if content:
        print(f"{prefix}{name}: {_preview(content)}", flush=True)


def _pending_interrupts(agent, config: dict) -> tuple:
    state = agent.get_state(config)
    return getattr(state, "interrupts", None) or ()


def _format_interrupt(intr) -> str:
    value = getattr(intr, "value", intr)
    if not isinstance(value, dict):
        return str(value)

    # batched HITLRequest
    requests = value.get("action_requests") or []
    if requests:
        lines = ["ACTION NEEDS YOUR APPROVAL:"]
        for req in requests:
            name = req.get("name", "?")
            args = req.get("args") or {}
            lines.append(f"  tool: {name}")
            lines.append(f"  args: {json.dumps(args, ensure_ascii=False)}")
            desc = req.get("description")
            if desc:
                lines.append(f"  note: {_preview(desc, 200)}")
        lines.append("Reply: yes / approve   OR   no / reject [reason]")
        return "\n".join(lines)

    # per_call ToolApprovalRequest
    if value.get("type") == "tool_approval":
        return (
            "ACTION NEEDS YOUR APPROVAL:\n"
            f"  tool: {value.get('name')}\n"
            f"  args: {json.dumps(value.get('args') or {}, ensure_ascii=False)}\n"
            "Reply: yes / approve   OR   no / reject [reason]"
        )

    return json.dumps(value, ensure_ascii=False, indent=2)


def _parse_approval(text: str) -> dict[str, Any] | None:
    """Map user reply to a HITL decision, or None if not an approval reply."""
    raw = text.strip()
    lower = raw.lower()

    if lower in {"y", "yes", "ok", "okay", "approve", "confirm", "اوه", "باشه", "تایید", "تأیید"}:
        return {"type": "approve"}

    if lower in {"n", "no", "reject", "cancel", "نه", "لغو"}:
        return {"type": "reject", "message": "User rejected the action."}

    if lower.startswith("reject ") or lower.startswith("no "):
        reason = raw.split(" ", 1)[1].strip() or "User rejected the action."
        return {"type": "reject", "message": reason}

    return None


def _resume_payload(intr, decision: dict[str, Any]) -> Any:
    """Build Command(resume=...) value for batched or per_call interrupt shapes."""
    value = getattr(intr, "value", intr)
    if isinstance(value, dict) and value.get("action_requests"):
        n = len(value["action_requests"])
        return {"decisions": [decision] * n}
    # per_call: single Decision
    return decision


def stream_agent(agent, payload, config: dict) -> tuple[str | None, bool]:
    """Stream until idle or interrupt. Returns (final_text, hit_interrupt)."""
    print("... working (live log below)", flush=True)
    t0 = time.time()
    final_text: str | None = None
    hit_interrupt = False

    for chunk in agent.stream(payload, config=config, stream_mode="updates"):
        if not isinstance(chunk, dict):
            continue
        for node, update in chunk.items():
            elapsed = time.time() - t0
            print(f"[{elapsed:5.1f}s] {node}", flush=True)

            if node == "__interrupt__":
                hit_interrupt = True
                continue

            if not isinstance(update, dict):
                continue
            messages = update.get("messages") or []
            for msg in messages[-3:]:
                _print_message(msg)
                content = getattr(msg, "content", None)
                tool_calls = getattr(msg, "tool_calls", None)
                if content and not tool_calls and getattr(msg, "type", "") == "ai":
                    final_text = content if isinstance(content, str) else str(content)

    print(f"... done in {time.time() - t0:.1f}s\n", flush=True)
    return final_text, hit_interrupt


def run_user_message(agent, user: str, config: dict) -> str | None:
    """Handle a normal chat turn, or an approval reply if an interrupt is pending."""
    from langgraph.types import Command

    pending = _pending_interrupts(agent, config)
    if pending:
        decision = _parse_approval(user)
        if decision is None:
            print(
                "\nA booking action is waiting for approval.\n"
                f"{_format_interrupt(pending[0])}\n",
                flush=True,
            )
            return None

        payload = Command(resume=_resume_payload(pending[0], decision))
        final, hit_interrupt = stream_agent(agent, payload, config)
        if hit_interrupt:
            for intr in _pending_interrupts(agent, config):
                print(_format_interrupt(intr), flush=True)
                print(flush=True)
            return None
        return final

    final, hit_interrupt = stream_agent(
        agent,
        {"messages": [{"role": "user", "content": user}]},
        config,
    )
    if hit_interrupt:
        for intr in _pending_interrupts(agent, config):
            print(_format_interrupt(intr), flush=True)
            print(flush=True)
        return None
    return final


def main() -> None:
    from agent.orchestrator import create_travel_orchestrator

    parser = argparse.ArgumentParser(description="Travel Deep Agent CLI")
    parser.add_argument(
        "--thread",
        default=None,
        help="Resume an existing thread_id (otherwise a new one is created)",
    )
    args = parser.parse_args()

    print("Travel Orchestrator (Deep Agent)", flush=True)
    print("Booking create/cancel will ask yes/no before running.", flush=True)
    print("Exit: quit / exit\n", flush=True)

    print("Loading MCP tools + agent...", flush=True)
    t0 = time.time()
    agent = create_travel_orchestrator()
    print(f"Ready in {time.time() - t0:.1f}s\n", flush=True)

    thread_id = args.thread or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"thread_id: {thread_id}", flush=True)
    print("(Reuse with: .\\.venv\\Scripts\\python.exe -m agent --thread <id>)\n", flush=True)

    # If resuming a thread that already paused for approval, show it immediately.
    for intr in _pending_interrupts(agent, config):
        print(_format_interrupt(intr), flush=True)
        print(flush=True)

    while True:
        try:
            user = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user.lower() in {"quit", "exit", "q"}:
            break

        try:
            final = run_user_message(agent, user, config)
        except Exception as exc:  # noqa: BLE001 — show CLI errors clearly
            print(f"\nERROR: {type(exc).__name__}: {exc}\n", flush=True)
            continue

        if final:
            print(f"Assistant> {final}\n", flush=True)
        elif not _pending_interrupts(agent, config):
            state = agent.get_state(config)
            values = getattr(state, "values", None) or {}
            messages = values.get("messages") or []
            if messages:
                last = messages[-1]
                print(f"Assistant> {getattr(last, 'content', last)}\n", flush=True)


if __name__ == "__main__":
    main()
