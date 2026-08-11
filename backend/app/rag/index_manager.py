"""
Lazy-loaded singleton access to the built vector + keyword indexes (§45:
"preloaded vector index... no unnecessary model reload").
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings
from app.rag.embeddings import get_embedding_model
from app.rag.hybrid import HybridRetriever
from app.rag.keyword_store import KeywordStore
from app.rag.vector_store import VectorStore

logger = logging.getLogger("drdoom.rag")


class IndexUnavailable(RuntimeError):
    """Raised when the knowledge base index has not been built yet."""


@lru_cache
def get_retriever() -> HybridRetriever:
    settings = get_settings()
    path = settings.VECTOR_INDEX_PATH
    if not VectorStore.exists(path) or not KeywordStore.exists(path):
        raise IndexUnavailable(
            f"No knowledge base index found at '{path}'. Run "
            "`python scripts/ingest_documents.py` first."
        )
    vector_store = VectorStore.load(path)
    keyword_store = KeywordStore.load(path)
    logger.info("Loaded knowledge base index: %d chunks", len(vector_store.chunks))
    return HybridRetriever(vector_store, keyword_store)


def index_is_ready() -> bool:
    settings = get_settings()
    return VectorStore.exists(settings.VECTOR_INDEX_PATH) and KeywordStore.exists(settings.VECTOR_INDEX_PATH)


def warm_up() -> bool:
    """Called at startup to preload the index and embedding model so the
    first real request isn't slow. Never raises — health checks stay honest
    about readiness instead of crashing the app (§70, §76)."""
    try:
        get_embedding_model()
        if index_is_ready():
            get_retriever()
            return True
        logger.warning("Knowledge base index not built yet; retrieval will be unavailable.")
        return False
    except Exception:  # noqa: BLE001
        logger.exception("Failed to warm up RAG index")
        return False
