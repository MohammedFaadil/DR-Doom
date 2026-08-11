"""
FAISS-backed embedded vector store — no separate server process (§9).

Persists:
  <path>/vectors.faiss   — the FAISS index (cosine similarity via inner
                            product over L2-normalized vectors)
  <path>/chunks.json     — parallel list of DocumentChunk metadata, index i
                            in this list corresponds to vector row i
"""
from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from app.rag.types import DocumentChunk


class VectorStore:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: list[DocumentChunk] = []

    def add(self, vectors: np.ndarray, chunks: list[DocumentChunk]) -> None:
        assert vectors.shape[0] == len(chunks)
        self.index.add(vectors.astype("float32"))
        self.chunks.extend(chunks)

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[DocumentChunk, float]]:
        if self.index.ntotal == 0:
            return []
        query_vector = query_vector.reshape(1, -1).astype("float32")
        scores, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        results: list[tuple[DocumentChunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results

    def save(self, path: str) -> None:
        out_dir = Path(path)
        out_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(out_dir / "vectors.faiss"))
        with open(out_dir / "chunks.json", "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self.chunks], f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "VectorStore":
        in_dir = Path(path)
        index = faiss.read_index(str(in_dir / "vectors.faiss"))
        with open(in_dir / "chunks.json", "r", encoding="utf-8") as f:
            chunk_dicts = json.load(f)
        store = cls(dimension=index.d)
        store.index = index
        store.chunks = [DocumentChunk.from_dict(d) for d in chunk_dicts]
        return store

    @staticmethod
    def exists(path: str) -> bool:
        in_dir = Path(path)
        return (in_dir / "vectors.faiss").exists() and (in_dir / "chunks.json").exists()
