"""Load the on-disk index and retrieve knowledge chunks.

Knowledge markdown is Persian-first. Queries are normalized (ی/ک, ZWNJ).
English queries get a small EN→FA expansion bridge.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bm25 import BM25
from .chunking import Chunk
from .normalize import expand_query, resolve_city

INDEX_DIR = Path(__file__).resolve().parent / "index"
INDEX_FILE = INDEX_DIR / "bm25_index.json"


@dataclass
class SearchHit:
    chunk: Chunk
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "city": self.chunk.city,
            "source": self.chunk.source,
            "heading": self.chunk.heading,
            "text": self.chunk.text,
        }


class KnowledgeRetriever:
    """BM25 retriever over markdown knowledge chunks."""

    def __init__(self, index_path: Path | None = None) -> None:
        self.index_path = index_path or INDEX_FILE
        self.chunks: list[Chunk] = []
        self.bm25: BM25 | None = None
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"RAG index not found at {self.index_path}. "
                "Run: python -m rag build"
            )
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.chunks = [Chunk.from_dict(c) for c in data["chunks"]]
        self.bm25 = BM25.from_state(data["bm25"])

    def search(
        self,
        query: str,
        city: str | None = None,
        top_k: int = 4,
    ) -> list[SearchHit]:
        """Search knowledge base. `city` filters to a folder name (istanbul, dubai)."""
        if self.bm25 is None:
            raise RuntimeError("Index not loaded")

        expanded = expand_query(query)
        scores = self.bm25.score(expanded)
        city_key = resolve_city(city)

        ranked: list[tuple[float, int]] = []
        for i, score in enumerate(scores):
            if score <= 0:
                continue
            if city_key and self.chunks[i].city != city_key:
                continue
            ranked.append((score, i))

        ranked.sort(key=lambda x: x[0], reverse=True)
        hits: list[SearchHit] = []
        for score, i in ranked[:top_k]:
            hits.append(SearchHit(chunk=self.chunks[i], score=score))
        return hits


def search_knowledge(
    query: str,
    city: str | None = None,
    top_k: int = 4,
) -> list[dict[str, Any]]:
    """Convenience wrapper used by MCP tool / CLI."""
    return [
        h.to_dict()
        for h in KnowledgeRetriever().search(query, city=city, top_k=top_k)
    ]
