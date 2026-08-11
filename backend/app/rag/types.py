"""Shared data types for the RAG subsystem."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    title: str
    organization: str
    url: str
    source_type: str  # "health_topic" | "drug_info"
    medical_domain: str
    section_heading: str
    text: str
    # Stable semantic label (see app/rag/sections.py) — what part of the
    # source document this chunk is. Answer composition selects by this
    # rather than by fragile heading-substring matching, which is essential
    # because ~half the source topics carry no headings at all.
    section_category: str = "overview"
    tags: list[str] = field(default_factory=list)
    document_type: str = "consumer health summary"
    country: str = "US"
    version: str = "1"
    last_reviewed: str | None = None
    publication_date: str | None = None

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "DocumentChunk":
        # Tolerate indexes built before a field was added, so a stale index
        # degrades gracefully instead of crashing at startup.
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    rerank_score: float = 0.0
