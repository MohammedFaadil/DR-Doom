"""
MedicationSafetyEngine (§20).

Answers medication questions ONLY from ingested MedlinePlus drug-info
chunks (source_type == "drug_info"). Never invents a drug name, dose,
contraindication, or interaction. If the knowledge base has no entry for
the requested drug, it refuses per §20/§90 rather than falling back to
general model "knowledge".
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.rag.index_manager import IndexUnavailable, get_retriever
from app.rag.types import RetrievedChunk

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I can't safely recommend or explain that medication based on the information "
    "currently available in my verified knowledge base. Please discuss it with a "
    "pharmacist or clinician."
)

PRECAUTION_HEADING_HINTS = (
    "precaution", "warning", "should not", "before taking", "should not take",
    "should i know", "special", "who should not",
)
SIDE_EFFECT_HEADING_HINTS = ("side effect", "adverse")
OVERDOSE_HEADING_HINTS = ("overdose", "emergency")


@dataclass
class MedicationInfo:
    drug_name: str
    found: bool
    uses: list[str] = field(default_factory=list)
    precautions: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    overdose_info: list[str] = field(default_factory=list)
    caution_flags: list[str] = field(default_factory=list)
    evidence: list[RetrievedChunk] = field(default_factory=list)


def _heading_matches(heading: str, hints: tuple[str, ...]) -> bool:
    lowered = heading.lower()
    return any(h in lowered for h in hints)


def lookup_medication(drug_name: str, patient_state: dict | None = None) -> MedicationInfo:
    state = patient_state or {}
    try:
        retriever = get_retriever()
    except IndexUnavailable:
        return MedicationInfo(drug_name=drug_name, found=False)

    result = retriever.retrieve(drug_name, top_k=10)
    drug_chunks = [c for c in result.chunks if c.chunk.source_type == "drug_info"]

    # Require the retrieved drug doc to plausibly be about the asked drug
    # (title contains the query) rather than trusting semantic similarity
    # alone — prevents e.g. "aspirin" retrieving ibuprofen info.
    name_lower = drug_name.lower().strip()
    matching = [c for c in drug_chunks if name_lower in c.chunk.title.lower() or name_lower in c.chunk.doc_id.lower()]
    if not matching:
        return MedicationInfo(drug_name=drug_name, found=False)

    info = MedicationInfo(drug_name=matching[0].chunk.title, found=True, evidence=matching)
    for c in matching:
        heading = c.chunk.section_heading
        if _heading_matches(heading, PRECAUTION_HEADING_HINTS):
            info.precautions.append(c.chunk.text)
        elif _heading_matches(heading, SIDE_EFFECT_HEADING_HINTS):
            info.side_effects.append(c.chunk.text)
        elif _heading_matches(heading, OVERDOSE_HEADING_HINTS):
            info.overdose_info.append(c.chunk.text)
        elif "why" in heading.lower() or "used" in heading.lower() or "use " in heading.lower():
            info.uses.append(c.chunk.text)

    allergies = [a.lower() for a in state.get("allergies", [])]
    if any(name_lower in a or a in name_lower for a in allergies):
        info.caution_flags.append(
            "You listed this medication (or something in its class) as an allergy. "
            "Do not take it — discuss safe alternatives with a pharmacist or clinician."
        )
    if state.get("pregnancy_status") == "pregnant":
        info.caution_flags.append(
            "Medication safety in pregnancy depends on the specific drug and trimester — "
            "confirm with a clinician or pharmacist before taking this."
        )
    age = state.get("age")
    if age is not None and age < 12:
        info.caution_flags.append(
            "This information is written for adults. Pediatric dosing and safety can differ "
            "significantly — confirm with a pediatrician or pharmacist before giving this to a child."
        )
    if age is not None and age >= 65:
        info.caution_flags.append(
            "Older adults can be more sensitive to some medications and interactions — "
            "confirm with a pharmacist or clinician, especially if taking other medications."
        )

    return info
