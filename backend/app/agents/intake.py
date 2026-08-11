"""
Intake Agent (§52.1): extracts structured patient information from free
text and merges it into the conversation's patient_state. Deterministic
extraction (symptom lexicon + regex), not free-form LLM extraction — so its
output is always valid, auditable JSON (§53).
"""
from __future__ import annotations

import re

from app.clinical.symptom_lexicon import extract_symptoms

_AGE_RE = re.compile(r"\b(\d{1,3})\s*(?:years?\s*old|yo|y/o|years?)\b")
_AGE_MONTHS_RE = re.compile(r"\b(\d{1,2})\s*month[s]?\s*old\b")
_FACTUAL_QUESTION_RE = re.compile(
    r"^(what|why|how|when|is|are|can|does|do)\b.*\b(cause|causes|treat|treatment|mean|work|prevent|is)\b", re.I
)
_FIRST_PERSON_SYMPTOM_RE = re.compile(r"\b(i (have|am|feel|experienc\w*|\'ve|got)|my \w+ (hurts|is))\b", re.I)


def detect_intent(text: str, has_active_symptoms: bool) -> str:
    """§65: don't start structured intake for a general factual question."""
    lowered = text.strip().lower()
    if has_active_symptoms:
        return "symptom_assessment"
    if re.search(r"\b(what is|what are|tell me about)\b.*\b(medication|drug|dose|pill)\b", lowered):
        return "medication_question"
    if _FIRST_PERSON_SYMPTOM_RE.search(lowered):
        return "symptom_assessment"
    if _FACTUAL_QUESTION_RE.match(lowered) or lowered.endswith("?"):
        return "factual_question"
    if extract_symptoms(text):
        return "symptom_assessment"
    return "factual_question"


def extract_age(text: str) -> tuple[float, str] | None:
    m = _AGE_MONTHS_RE.search(text.lower())
    if m:
        return float(m.group(1)), "months"
    m = _AGE_RE.search(text.lower())
    if m:
        return float(m.group(1)), "years"
    return None


def apply_intake(patient_state: dict, user_text: str, is_answer: bool = False) -> dict:
    """Merge newly-extracted information from `user_text` into
    `patient_state` (a plain dict mirroring schemas.clinical.PatientState)
    and return the updated dict.

    `is_answer=True` means `user_text` is the display label of an answer to
    a specific typed question (e.g. a multi_select option like "Severe
    headache" picked to describe a symptom *associated with* the real
    complaint) rather than a fresh message from the user. Symptom
    extraction is skipped in that case — the option label is deliberately
    drawn from the same clinical vocabulary as the symptom lexicon, so
    running extraction on it would misfile "I also have a headache along
    with my fever" as a brand-new, unrelated top-level complaint instead of
    an associated symptom (which app/agents/question.py already records
    correctly via the structured answer). Emergency screening still runs on
    the raw answer text regardless (app/agents/orchestrator.py, step 1), so
    red-flag detection is never skipped.
    """
    state = dict(patient_state)
    state.setdefault("symptoms", [])
    state.setdefault("red_flags", [])
    state.setdefault("medications", [])
    state.setdefault("allergies", [])
    state.setdefault("medical_history", [])
    state.setdefault("missing_information", [])
    state.setdefault("asked_question_ids", [])

    if state.get("age") is None:
        age_match = extract_age(user_text)
        if age_match:
            state["age"], state["age_unit"] = age_match

    if not is_answer:
        existing_names = {s["name"] for s in state["symptoms"]}
        newly_found = [sd for sd in extract_symptoms(user_text) if sd.canonical not in existing_names]
        for sd in newly_found:
            state["symptoms"].append({"name": sd.canonical, "domain": sd.domain, "severity": None, "duration": None})
            existing_names.add(sd.canonical)

        if newly_found:
            # The user is now actively describing a new, distinct complaint
            # — make it the focus of the remaining questions instead of
            # staying anchored to whatever was mentioned first (§65).
            state["primary_complaint"] = newly_found[-1].canonical
        elif state.get("primary_complaint") is None and state["symptoms"]:
            state["primary_complaint"] = state["symptoms"][0]["name"]

    # Intent must be sticky once an assessment is underway. Re-deriving it
    # from each turn's raw text breaks the flow: answering "28" to the age
    # question is not, on its own, a factual question — but that's exactly
    # how a bare number classifies in isolation, which previously dropped
    # the user out of the clinical flow mid-consultation.
    assessment_in_progress = bool(state["symptoms"]) or bool(state.get("asked_question_ids"))
    if is_answer and assessment_in_progress:
        state.setdefault("intent", "symptom_assessment")
        if state["intent"] == "unknown":
            state["intent"] = "symptom_assessment"
    else:
        state["intent"] = detect_intent(user_text, bool(state["symptoms"]))

    return state
