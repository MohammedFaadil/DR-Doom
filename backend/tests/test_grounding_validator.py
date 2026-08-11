import pytest

from app.rag.index_manager import index_is_ready
from app.rag.hybrid import HybridRetriever
from app.rag.keyword_store import KeywordStore
from app.rag.vector_store import VectorStore
from app.config import get_settings
from app.safety.grounding_validator import validate_grounding

pytestmark = pytest.mark.skipif(
    not index_is_ready(), reason="Knowledge base index not built — run scripts/ingest_documents.py first."
)


def _retriever():
    settings = get_settings()
    return HybridRetriever(VectorStore.load(settings.VECTOR_INDEX_PATH), KeywordStore.load(settings.VECTOR_INDEX_PATH))


def test_grounded_text_passes_validation():
    retrieval = _retriever().retrieve("migraine headache symptoms")
    evidence = retrieval.chunks[:3]
    # Text built directly from the evidence should be fully supported.
    text = " ".join(c.chunk.text for c in evidence)
    result = validate_grounding(text, evidence)
    assert result.confidence > 0.5
    assert len(result.unsupported_sentences) == 0


def test_fabricated_claim_is_flagged_unsupported():
    retrieval = _retriever().retrieve("migraine headache symptoms")
    evidence = retrieval.chunks[:3]
    fabricated = "Dr. Jonathan Smith invented a cure for migraines in 1997 using purple light therapy exclusively."
    result = validate_grounding(fabricated, evidence)
    assert fabricated.strip() not in result.grounded_text or len(result.unsupported_sentences) > 0


def test_empty_evidence_yields_zero_confidence():
    result = validate_grounding("Some claim.", [])
    assert result.confidence == 0.0
