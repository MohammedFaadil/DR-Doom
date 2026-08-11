"""
Lightweight reranker (§11, §87-88).

No cross-encoder model is loaded (keeps the default deployment light) —
instead this combines the hybrid semantic+keyword score with two
deterministic, explainable signals:
  * source-authority weighting (§88): government/NIH sources rank first —
    in this build every source IS MedlinePlus/NIH, so this mainly guards
    the interface for when other sources are added later
  * heading/domain match boost: a chunk whose section heading or medical
    domain textually matches the query gets a small boost

This keeps reranking real and inspectable rather than an opaque model call.
"""
from __future__ import annotations

from app.rag.keyword_store import tokenize
from app.rag.types import RetrievedChunk

AUTHORITY_WEIGHT = {
    "National Library of Medicine": 1.0,
    "MedlinePlus": 1.0,
}


def rerank(query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
    query_tokens = set(tokenize(query))
    for cand in candidates:
        authority = AUTHORITY_WEIGHT.get(cand.chunk.organization, 0.9)
        heading_tokens = set(tokenize(cand.chunk.section_heading))
        heading_overlap = len(query_tokens & heading_tokens)
        boost = 1.0 + min(heading_overlap * 0.03, 0.12)
        cand.rerank_score = cand.combined_score * authority * boost
    return sorted(candidates, key=lambda c: c.rerank_score, reverse=True)
