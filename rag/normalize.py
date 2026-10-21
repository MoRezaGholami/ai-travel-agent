"""Persian-first text normalization for RAG.

Knowledge markdown is written in Persian, so queries match documents directly.
We still normalize spelling variants (Arabic/Persian letters, ZWNJ) so retrieval
stays stable across different user keyboards.
"""

from __future__ import annotations

import re

_ARABIC_YEH = "\u064a"  # ي
_PERSIAN_YEH = "\u06cc"  # ی
_ARABIC_KAF = "\u0643"  # ك
_PERSIAN_KAF = "\u06a9"  # ک
_ALEF_VARIANTS = {
    "\u0622": "ا",
    "\u0623": "ا",
    "\u0625": "ا",
    "\u0627": "ا",
}
_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_WHITESPACE = re.compile(r"\s+")

# Map FA/EN city labels → knowledge folder names
CITY_ALIASES: dict[str, str] = {
    "istanbul": "istanbul",
    "استانبول": "istanbul",
    "dubai": "dubai",
    "دبی": "dubai",
    "دبي": "dubai",
    "baku": "baku",
    "باکو": "baku",
    "doha": "doha",
    "دوحه": "doha",
    "ankara": "ankara",
    "آنکارا": "ankara",
    "انکارا": "ankara",
    "paris": "paris",
    "پاریس": "paris",
    "frankfurt": "frankfurt",
    "فرانکفورت": "frankfurt",
    "london": "london",
    "لندن": "london",
    "rome": "rome",
    "رم": "rome",
    "roma": "rome",
    "kuala lumpur": "kuala_lumpur",
    "kuala_lumpur": "kuala_lumpur",
    "kualalumpur": "kuala_lumpur",
    "کوالالامپور": "kuala_lumpur",
    "کوالا لامپور": "kuala_lumpur",
    "bangkok": "bangkok",
    "بانکوک": "bangkok",
    "بانگکوک": "bangkok",
}

# Optional: tiny EN→FA bridge if someone queries in English against Persian KB
EN_FA_LEXICON: dict[str, str] = {
    "attractions": "جاذبه دیدنی",
    "attraction": "جاذبه",
    "neighborhood": "محله اقامت",
    "neighbourhood": "محله اقامت",
    "where to stay": "کجا اقامت محله",
    "transport": "حمل و نقل مترو فرودگاه",
    "metro": "مترو حمل و نقل",
    "airport": "فرودگاه",
    "culture": "آداب فرهنگ نکات",
    "etiquette": "آداب",
    "budget": "بودجه هزینه",
    "desert": "صحرا سافاری",
    "beach": "ساحل",
    "overview": "معرفی",
}


def normalize_text(text: str) -> str:
    """Normalize Persian/Arabic letters and collapse whitespace."""
    if not text:
        return ""
    t = text.strip().lower()
    t = t.replace(_ARABIC_YEH, _PERSIAN_YEH).replace(_ARABIC_KAF, _PERSIAN_KAF)
    for src, dst in _ALEF_VARIANTS.items():
        t = t.replace(src, dst)
    t = _DIACRITICS.sub("", t)
    t = t.replace("\u200c", " ")  # ZWNJ → space
    t = _WHITESPACE.sub(" ", t)
    return t.strip()


def resolve_city(city: str | None) -> str | None:
    """Map FA/EN city names to knowledge folder names under rag/knowledge/."""
    if not city:
        return None
    key = normalize_text(city)
    for alias, folder in CITY_ALIASES.items():
        if normalize_text(alias) == key:
            return folder
    return key


def expand_query(query: str) -> str:
    """Normalize query; optionally add Persian terms for English keywords."""
    normalized = normalize_text(query)
    extras: list[str] = []
    for en, fa in sorted(EN_FA_LEXICON.items(), key=lambda x: len(x[0]), reverse=True):
        if en in normalized:
            extras.append(fa)
    if extras:
        return f"{normalized} {' '.join(extras)}"
    return normalized
