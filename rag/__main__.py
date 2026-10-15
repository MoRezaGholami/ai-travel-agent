"""CLI:
  python -m rag build
  python -m rag search "جاذبه‌های استانبول" --city استانبول
  python -m rag search "desert safari" --city dubai
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rag", description="Travel RAG tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build", help="Rebuild BM25 index from knowledge/*.md")

    p_search = sub.add_parser("search", help="Search the knowledge index")
    p_search.add_argument("query", help="Query in Persian or English")
    p_search.add_argument("--city", default=None, help="Filter: istanbul/dubai or استانبول/دبی")
    p_search.add_argument("--top-k", type=int, default=4)

    args = parser.parse_args(argv)

    if args.cmd == "build":
        from .build_index import build_index

        path = build_index()
        print(f"Index written: {path}")
        return 0

    if args.cmd == "search":
        from .retriever import search_knowledge

        hits = search_knowledge(args.query, city=args.city, top_k=args.top_k)
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
