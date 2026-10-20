"""Interactive CLI for the travel orchestrator.

Run:
  .\\.venv\\Scripts\\python.exe -m agent
"""

from __future__ import annotations

import argparse
import json
import time
import uuid

from agent.session import approve, chat, get_pending, pending_interrupts


def _print_pending(result) -> None:
    print("ACTION NEEDS YOUR APPROVAL:", flush=True)
    for p in result.pending:
        print(f"  tool: {p.tool}", flush=True)
        print(f"  args: {json.dumps(p.args, ensure_ascii=False)}", flush=True)
        if p.description:
            note = str(p.description).replace("\n", " ")[:200]
            print(f"  note: {note}", flush=True)
    print("Reply: yes / approve   OR   no / reject [reason]", flush=True)
    print(flush=True)


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
    print(f"thread_id: {thread_id}", flush=True)
    print("(Reuse with: .\\.venv\\Scripts\\python.exe -m agent --thread <id>)\n", flush=True)

    pending = get_pending(agent, thread_id)
    if pending.status == "needs_approval":
        _print_pending(pending)

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

        lower = user.lower()
        try:
            if pending_interrupts(agent, thread_id):
                if lower in {"y", "yes", "ok", "okay", "approve", "confirm", "باشه", "تایید", "تأیید"}:
                    print("... approving", flush=True)
                    result = approve(agent, thread_id, decision="approve")
                elif lower in {"n", "no", "reject", "cancel", "نه", "لغو"} or lower.startswith(
                    ("reject ", "no ")
                ):
                    reason = (
                        user.split(" ", 1)[1].strip()
                        if " " in user
                        else "User rejected the action."
                    )
                    print("... rejecting", flush=True)
                    result = approve(agent, thread_id, decision="reject", reason=reason)
                else:
                    _print_pending(get_pending(agent, thread_id))
                    continue
            else:
                print("... working", flush=True)
                result = chat(agent, thread_id, user)
        except Exception as exc:  # noqa: BLE001
            print(f"\nERROR: {type(exc).__name__}: {exc}\n", flush=True)
            continue

        if result.status == "error":
            print(f"\nERROR: {result.error}\n", flush=True)
        elif result.status == "needs_approval":
            if result.reply:
                print(f"\nAssistant> {result.reply}\n", flush=True)
            _print_pending(result)
        elif result.reply:
            print(f"\nAssistant> {result.reply}\n", flush=True)


if __name__ == "__main__":
    main()
