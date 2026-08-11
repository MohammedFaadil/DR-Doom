"""BM25 keyword index (rank_bm25) — the "keyword search" half of hybrid
retrieval (§11). Kept in-process, no separate search server."""
from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.rag.types import DocumentChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class KeywordStore:
    def __init__(self) -> None:
        self.bm25: BM25Okapi | None = None
        self.chunks: list[DocumentChunk] = []

    def build(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks
        corpus = [tokenize(f"{c.title} {c.section_heading} {c.text}") for c in chunks]
        self.bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int) -> list[tuple[DocumentChunk, float]]:
        if self.bm25 is None or not self.chunks:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        max_score = max(scores) if len(scores) else 0.0
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)[:top_k]
        # normalize to [0, 1] so it can be blended with cosine-similarity semantic scores
        return [(c, (s / max_score) if max_score > 0 else 0.0) for c, s in ranked]

    def save(self, path: str) -> None:
        out_dir = Path(path)
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "bm25.pkl", "wb") as f:
            pickle.dump(self.bm25, f)
        with open(out_dir / "bm25_chunks.json", "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self.chunks], f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "KeywordStore":
        in_dir = Path(path)
        store = cls()
        with open(in_dir / "bm25.pkl", "rb") as f:
            store.bm25 = pickle.load(f)
        with open(in_dir / "bm25_chunks.json", "r", encoding="utf-8") as f:
            store.chunks = [DocumentChunk.from_dict(d) for d in json.load(f)]
        return store

    @staticmethod
    def exists(path: str) -> bool:
        in_dir = Path(path)
        return (in_dir / "bm25.pkl").exists() and (in_dir / "bm25_chunks.json").exists()
