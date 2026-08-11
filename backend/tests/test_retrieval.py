import pytest

from app.config import get_settings
from app.rag.hybrid import HybridRetriever
from app.rag.index_manager import index_is_ready
from app.rag.keyword_store import KeywordStore
from app.rag.vector_store import VectorStore

pytestmark = pytest.mark.skipif(
    not index_is_ready(), reason="Knowledge base index not built — run scripts/ingest_documents.py first."
)


def _retriever():
    settings = get_settings()
    return HybridRetriever(VectorStore.load(settings.VECTOR_INDEX_PATH), KeywordStore.load(settings.VECTOR_INDEX_PATH))


def test_headache_query_returns_headache_or_migraine_docs():
    result = _retriever().retrieve("throbbing headache with nausea")
    titles = {c.chunk.title.lower() for c in result.chunks}
    assert any("headache" in t or "migraine" in t for t in titles)


def test_all_citations_have_real_medlineplus_urls():
    result = _retriever().retrieve("asthma symptoms")
    for c in result.chunks:
        assert c.chunk.url.startswith("https://medlineplus.gov/")


def test_drug_query_retrieves_drug_info_chunks():
    result = _retriever().retrieve("ibuprofen side effects", top_k=10)
    assert any(c.chunk.source_type == "drug_info" for c in result.chunks)


def test_nonsense_query_returns_low_scores():
    result = _retriever().retrieve("asdkjhqwlkejhasdlkjhasd nonsense gibberish query")
    if result.chunks:
        assert result.chunks[0].rerank_score < 0.5
