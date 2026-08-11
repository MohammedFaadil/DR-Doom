"""Retrieval Agent (§52.4): builds a retrieval query from conversation
context/patient state and calls the hybrid retriever."""
from __future__ import annotations

from app.rag.hybrid import RetrievalResult
from app.rag.index_manager import get_retriever


def build_retrieval_query(state: dict, latest_text: str) -> str:
    """Query focuses on the primary complaint currently being assessed and
    its own associated symptoms — not every symptom ever mentioned in the
    conversation — so a fever assessment doesn't drag in an unrelated
    headache/cold document just because the patient mentioned one earlier
    (§65, §87 query rewriting should narrow retrieval, not broaden it)."""
    primary = state.get("primary_complaint")
    parts = [latest_text]
    if primary:
        parts.append(primary)
        for s in state.get("symptoms", []):
            if s.get("name") == primary:
                for assoc in s.get("associated_symptoms", []) or []:
                    label = str(assoc).replace("_", " ")
                    if label.lower() not in ("none", "none of these"):
                        parts.append(label)
                if s.get("location"):
                    parts.append(str(s["location"]).replace("_", " "))
                break
    else:
        for s in state.get("symptoms", []):
            parts.append(s.get("name", ""))
    return " ".join(p for p in parts if p)


def retrieve_evidence(state: dict, latest_text: str, top_k: int | None = None) -> RetrievalResult:
    """Retrieve without a hard metadata domain filter.

    An earlier version filtered candidates by the symptom lexicon's
    `domain`, but that couples two independently-maintained vocabularies:
    the lexicon has domains (e.g. "neurological") that no knowledge-base
    document carries, so the filter silently starved retrieval and returned
    wildly off-topic sources (a dizziness query matching only emergency
    documents). Topical focus is enforced later and more reliably in
    app/agents/explanation.py, which checks the retrieved document's own
    title against the complaint.
    """
    retriever = get_retriever()
    query = build_retrieval_query(state, latest_text)
    return retriever.retrieve(query, top_k=top_k)
