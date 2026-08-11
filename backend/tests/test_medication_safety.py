import pytest

from app.rag.index_manager import index_is_ready
from app.safety.medication_safety import lookup_medication

pytestmark = pytest.mark.skipif(
    not index_is_ready(), reason="Knowledge base index not built — run scripts/ingest_documents.py first."
)


def test_known_drug_found():
    info = lookup_medication("ibuprofen")
    assert info.found is True
    assert info.evidence


def test_unknown_drug_refuses():
    info = lookup_medication("totallymadeupdrugxyz123")
    assert info.found is False


def test_allergy_flag_raised():
    info = lookup_medication("ibuprofen", {"allergies": ["ibuprofen"]})
    assert any("allerg" in f.lower() for f in info.caution_flags)


def test_pediatric_flag_raised_for_young_child():
    info = lookup_medication("ibuprofen", {"age": 5})
    assert any("pediatric" in f.lower() or "child" in f.lower() for f in info.caution_flags)
