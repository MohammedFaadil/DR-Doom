"""
Hybrid retrieval engine (§9, §11): semantic (FAISS) + keyword (BM25),
combined with configurable weights, then reranked, then optionally filtered
by metadata (medical_domain / tags).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from app.config import get_settings
from app.rag.embeddings import get_embedding_model
from app.rag.keyword_store import KeywordStore
from app.rag.normalization import normalize_query
from app.rag.rerank import rerank
from app.rag.types import DocumentChunk, RetrievedChunk
from app.rag.vector_store import VectorStore

settings = get_settings()


@dataclass
class RetrievalResult:
    query: str
    rewritten_query: str
    chunks: list[RetrievedChunk]
    semantic_latency_ms: float
    keyword_latency_ms: float
    total_latency_ms: float


class HybridRetriever:
    def __init__(self, vector_store: VectorStore, keyword_store: KeywordStore) -> None:
        self.vector_store = vector_store
        self.keyword_store = keyword_store
        self.embedding_model = get_embedding_model()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        medical_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> RetrievalResult:
        top_k = top_k or settings.RETRIEVAL_TOP_K
        rewritten = normalize_query(query)
        fetch_k = max(top_k * 4, 20)

        t0 = time.perf_counter()
        query_vec = self.embedding_model.embed_one(rewritten)
        semantic_hits = self.vector_store.search(query_vec, fetch_k)
        t1 = time.perf_counter()

        keyword_hits = self.keyword_store.search(rewritten, fetch_k)
        t2 = time.perf_counter()

        merged: dict[str, RetrievedChunk] = {}
        for chunk, score in semantic_hits:
            merged[chunk.chunk_id] = RetrievedChunk(chunk=chunk, semantic_score=score)
        for chunk, score in keyword_hits:
            existing = merged.get(chunk.chunk_id)
            if existing:
                existing.keyword_score = score
            else:
                merged[chunk.chunk_id] = RetrievedChunk(chunk=chunk, keyword_score=score)

        candidates = list(merged.values())
        if medical_domains:
            candidates = [c for c in candidates if c.chunk.medical_domain in medical_domains]
        if exclude_domains:
            candidates = [c for c in candidates if c.chunk.medical_domain not in exclude_domains]

        for c in candidates:
            c.combined_score = (
                settings.HYBRID_SEMANTIC_WEIGHT * c.semantic_score
                + settings.HYBRID_KEYWORD_WEIGHT * c.keyword_score
            )

        ranked = rerank(rewritten, candidates)[:top_k]
        total_ms = (time.perf_counter() - t0) * 1000

        return RetrievalResult(
            query=query,
            rewritten_query=rewritten,
            chunks=ranked,
            semantic_latency_ms=(t1 - t0) * 1000,
            keyword_latency_ms=(t2 - t1) * 1000,
            total_latency_ms=total_ms,
        )
