"""Medication Safety Agent (§20, §52.6): resolves a medication question to
a known ingested drug and formats a safe, evidence-only response."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.knowledge_config import DRUGS
from app.rag.types import RetrievedChunk
from app.safety.medication_safety import INSUFFICIENT_EVIDENCE_MESSAGE, lookup_medication

_KNOWN_DRUG_NAMES = [d.name for d in DRUGS]


@dataclass
class MedicationAnswer:
    message: str
    evidence: list[RetrievedChunk] = field(default_factory=list)


def _extract_drug_name(text: str) -> str | None:
    lowered = text.lower()
    for name in _KNOWN_DRUG_NAMES:
        if re.search(r"\b" + re.escape(name) + r"\b", lowered):
            return name
    return None


def answer_medication_question(user_text: str, patient_state: dict) -> MedicationAnswer:
    drug_name = _extract_drug_name(user_text)
    if not drug_name:
        return MedicationAnswer(INSUFFICIENT_EVIDENCE_MESSAGE)

    info = lookup_medication(drug_name, patient_state)
    if not info.found:
        return MedicationAnswer(INSUFFICIENT_EVIDENCE_MESSAGE)

    lines = [f"## Medication information: {info.drug_name}", ""]
    lines.append(
        "*This is general medication information to discuss with a qualified clinician or "
        "pharmacist — not a prescription order.*"
    )
    if info.uses:
        lines += ["", "### Common uses", " ".join(info.uses)]
    if info.precautions:
        lines += ["", "### Precautions", " ".join(info.precautions)]
    if info.side_effects:
        lines += ["", "### Possible side effects", " ".join(info.side_effects)]
    if info.overdose_info:
        lines += ["", "### In case of emergency/overdose", " ".join(info.overdose_info)]
    if info.caution_flags:
        lines += ["", "### Specific to you"] + [f"- {c}" for c in info.caution_flags]

    if info.evidence:
        lines += ["", "**Sources**"]
        seen = set()
        i = 1
        for c in info.evidence:
            if c.chunk.doc_id in seen:
                continue
            seen.add(c.chunk.doc_id)
            lines.append(f"{i}. [{c.chunk.organization} — {c.chunk.title}]({c.chunk.url})")
            i += 1

    return MedicationAnswer("\n".join(lines), info.evidence)
