"""Split markdown knowledge files into retrievable chunks."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .normalize import normalize_text

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
_HEADING = re.compile(r"(?m)^(#{1,3})\s+(.+)$")

# Persian topic tags (file stems are still English folder names)
STEM_TAGS: dict[str, str] = {
    "overview": "معرفی کلی بودجه فصل",
    "attractions": "جاذبه جاذبه ها دیدنی مکان های دیدنی",
    "neighborhoods": "محله محله ها اقامت کجا بمونم",
    "transport": "حمل و نقل مترو فرودگاه تاکسی فری",
    "culture_tips": "آداب فرهنگ نکات محلی انعام",
}


@dataclass
class Chunk:
    id: str
    city: str
    source: str  # relative path e.g. istanbul/attractions.md
    heading: str
    text: str
    text_normalized: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        return cls(**data)


def _split_markdown(text: str) -> list[tuple[str, str]]:
    """Return list of (heading, body) sections. Intro before first heading included."""
    matches = list(_HEADING.finditer(text))
    if not matches:
        body = text.strip()
        return [("", body)] if body else []

    sections: list[tuple[str, str]] = []
    # Content before first heading
    pre = text[: matches[0].start()].strip()
    if pre:
        sections.append(("", pre))

    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body or heading:
            sections.append((heading, body))
    return sections


def load_chunks(knowledge_dir: Path | None = None) -> list[Chunk]:
    """Walk knowledge/**/*.md and produce chunks (one per markdown section)."""
    root = knowledge_dir or KNOWLEDGE_DIR
    chunks: list[Chunk] = []
    if not root.exists():
        return chunks

    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        city = path.parent.name.lower()
        raw = path.read_text(encoding="utf-8")
        for idx, (heading, body) in enumerate(_split_markdown(raw)):
            # Skip title-only sections (e.g. H1 with all content under H2s)
            if len(body.strip()) < 40:
                continue
            piece = f"{heading}\n{body}".strip() if heading else body
            chunk_id = f"{rel}#{idx}"
            # Include file stem + city so FA lexicon terms (attractions/transport/...)
            # land on the right documents.
            tags = STEM_TAGS.get(path.stem, path.stem)
            # Repeat tags so topic terms outweigh accidental city-name overlap
            searchable = f"{piece} {tags} {tags} {city}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    city=city,
                    source=rel,
                    heading=heading or path.stem,
                    text=piece,
                    text_normalized=normalize_text(searchable),
                )
            )
    return chunks
