"""Interactive CLI for the travel orchestrator.

Run:
  python -m agent

Conversation memory:
  - Same process keeps one thread_id (multi-turn edits work).
  - State is stored in data/checkpoints.sqlite
  - Optional: python -m agent --thread <id> to resume a previous chat
"""

from __future__ import annotations

import argparse
import uuid


def main() -> None:
    from agent.orchestrator import create_travel_orchestrator

    parser = argparse.ArgumentParser(description="Travel Deep Agent CLI")
    parser.add_argument(
        "--thread",
        default=None,
        help="Resume an existing thread_id (otherwise a new one is created)",
    )
    args = parser.parse_args()

    print("Travel Orchestrator (Deep Agent)")
    print("Sample: Find a flight and hotel for a trip to Istanbul")
    print("Exit: quit / exit")
    print("Tip: Windows Terminal for Persian; CMD is fine in English.\n")

    agent = create_travel_orchestrator()
    thread_id = args.thread or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"thread_id: {thread_id}")
    print("(Reuse with: python -m agent --thread <id>)\n")

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

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user}]},
            config=config,
        )
        messages = result.get("messages") or []
        if messages:
            last = messages[-1]
            content = getattr(last, "content", last)
            print(f"\nAssistant> {content}\n")
        else:
            print(result)


if __name__ == "__main__":
    main()
