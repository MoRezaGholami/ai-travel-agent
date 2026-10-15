"""Minimal BM25 ranker (no sklearn/torch dependency)."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN = re.compile(r"[a-z0-9\u0600-\u06ff]+", re.IGNORECASE)

# Very common Persian particles that hurt BM25 on short travel docs
_STOPWORDS = {
    "و",
    "در",
    "از",
    "به",
    "که",
    "این",
    "را",
    "با",
    "برای",
    "تا",
    "یا",
    "هم",
    "یک",
    "ها",
    "های",
    "می",
    "نمی",
}

_SUFFIXES = ("های", "ها", "ان", "ات")


def _light_stem(token: str) -> str:
    """Strip common Persian plural/suffix forms: جاذبه‌های → جاذبه."""
    for suf in _SUFFIXES:
        if len(token) > len(suf) + 2 and token.endswith(suf):
            return token[: -len(suf)]
    return token


def tokenize(text: str) -> list[str]:
    tokens = [_light_stem(t) for t in _TOKEN.findall(text.lower())]
    return [t for t in tokens if t and t not in _STOPWORDS]


@dataclass
class BM25:
    k1: float = 1.5
    b: float = 0.75
    doc_freqs: list[Counter] | None = None
    doc_len: list[int] | None = None
    avgdl: float = 0.0
    ndocs: int = 0
    df: dict[str, int] | None = None
    idf: dict[str, float] | None = None

    def fit(self, corpus: list[str]) -> BM25:
        self.doc_freqs = []
        self.doc_len = []
        df: Counter[str] = Counter()
        for doc in corpus:
            tokens = tokenize(doc)
            self.doc_len.append(len(tokens))
            freqs = Counter(tokens)
            self.doc_freqs.append(freqs)
            for term in freqs:
                df[term] += 1
        self.ndocs = len(corpus)
        self.avgdl = sum(self.doc_len) / self.ndocs if self.ndocs else 0.0
        self.df = dict(df)
        self.idf = {
            term: math.log(1 + (self.ndocs - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }
        return self

    def score(self, query: str) -> list[float]:
        assert self.doc_freqs is not None and self.doc_len is not None
        assert self.idf is not None
        q_terms = tokenize(query)
        scores = [0.0] * self.ndocs
        for i, freqs in enumerate(self.doc_freqs):
            dl = self.doc_len[i]
            for term in q_terms:
                if term not in freqs:
                    continue
                tf = freqs[term]
                idf = self.idf.get(term, 0.0)
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
                scores[i] += idf * (tf * (self.k1 + 1)) / (denom or 1.0)
        return scores

    def to_state(self) -> dict:
        return {
            "k1": self.k1,
            "b": self.b,
            "doc_freqs": [dict(c) for c in (self.doc_freqs or [])],
            "doc_len": self.doc_len,
            "avgdl": self.avgdl,
            "ndocs": self.ndocs,
            "df": self.df,
            "idf": self.idf,
        }

    @classmethod
    def from_state(cls, state: dict) -> BM25:
        obj = cls(k1=state["k1"], b=state["b"])
        obj.doc_freqs = [Counter(d) for d in state["doc_freqs"]]
        obj.doc_len = state["doc_len"]
        obj.avgdl = state["avgdl"]
        obj.ndocs = state["ndocs"]
        obj.df = state["df"]
        obj.idf = state["idf"]
        return obj
