"""Build BM25 index from rag/knowledge/**/*.md."""

from __future__ import annotations

import json
from pathlib import Path

from .bm25 import BM25
from .chunking import load_chunks
from .retriever import INDEX_DIR, INDEX_FILE


def build_index(
    knowledge_dir: Path | None = None,
    index_path: Path | None = None,
) -> Path:
    """Re-read all markdown files and write bm25_index.json."""
    out = index_path or INDEX_FILE
    chunks = load_chunks(knowledge_dir)
    if not chunks:
        raise RuntimeError("No markdown chunks found under rag/knowledge/")

    corpus = [c.text_normalized for c in chunks]
    bm25 = BM25().fit(corpus)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "chunk_count": len(chunks),
        "chunks": [c.to_dict() for c in chunks],
        "bm25": bm25.to_state(),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
