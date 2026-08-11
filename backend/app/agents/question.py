"""
Question Agent (§13, §15, §52.2): decides the single next clinically
relevant question, or signals that enough information has been gathered.

Priority order follows §13 exactly: red flags (handled separately by the
EmergencyRiskEngine, always first) -> age -> sex -> pregnancy -> main
symptom details (location/onset/duration/severity/associated symptoms) ->
history -> medications -> allergies. Adaptive stopping (§65): the loop ends
as soon as no clinically-relevant unanswered question remains, capped by
MAX_QUESTIONS as a runaway-conversation safety valve.
"""
from __future__ import annotations

from app.clinical.question_bank.bank import GENERIC_FOLLOW_UP, PROFILE_QUESTIONS, Question, get_question_set
from app.clinical.symptom_lexicon import get_symptom

MAX_QUESTIONS = 9


def _profile_question_relevant(q: Question, state: dict) -> bool:
    if q["id"] == "pregnancy_status":
        sex = state.get("sex")
        age = state.get("age")
        if sex == "male":
            return False
        if age is not None and (age < 12 or age > 55):
            return False
        return True
    return True


def _symptom_field_answered(state: dict, primary_name: str, field: str) -> bool:
    for s in state.get("symptoms", []):
        if s.get("name") == primary_name:
            return s.get(field) not in (None, "", [])
    return False


def select_next_question(state: dict) -> Question | None:
    if state.get("intent") != "symptom_assessment":
        return None
    if len(state.get("asked_question_ids", [])) >= MAX_QUESTIONS:
        return None

    asked = set(state.get("asked_question_ids", []))
    candidates: list[Question] = []

    for q in PROFILE_QUESTIONS:
        if q["id"] in asked:
            continue
        if state.get(q["field"]) is not None:
            continue
        if not _profile_question_relevant(q, state):
            continue
        candidates.append(q)

    primary_name = state.get("primary_complaint")
    if primary_name:
        symptom_def = get_symptom(primary_name)
        if symptom_def:
            for q in get_question_set(symptom_def.question_set):
                if q["id"] in asked:
                    continue
                if _symptom_field_answered(state, primary_name, q["field"]):
                    continue
                candidates.append(q)

    # Generic follow-up only once the primary-symptom-specific questions are
    # exhausted, so the conversation feels focused rather than a long form.
    primary_symptom_pending = any(
        c["field"] not in ("age", "sex", "pregnancy_status") for c in candidates
    )
    if not primary_symptom_pending:
        for q in GENERIC_FOLLOW_UP:
            if q["id"] in asked:
                continue
            if state.get(q["field"]):
                continue
            candidates.append(q)

    if not candidates:
        return None

    candidates.sort(key=lambda q: q["clinical_priority"])
    return candidates[0]


def find_question_by_id(question_id: str) -> Question | None:
    for q in PROFILE_QUESTIONS:
        if q["id"] == question_id:
            return q
    for q in GENERIC_FOLLOW_UP:
        if q["id"] == question_id:
            return q
    for question_set in _all_question_sets():
        for q in question_set:
            if q["id"] == question_id:
                return q
    return None


def _all_question_sets():
    from app.clinical.question_bank.bank import QUESTION_SETS

    return QUESTION_SETS.values()


def record_question_asked(state: dict, question_id: str) -> dict:
    state = dict(state)
    asked = list(state.get("asked_question_ids", []))
    if question_id not in asked:
        asked.append(question_id)
    state["asked_question_ids"] = asked
    return state


def apply_answer(state: dict, question: Question, value) -> dict:
    """Merge a question's answer into patient_state, writing into the
    primary symptom's sub-dict for symptom-specific fields.

    `value` should be the structured answer (ChatRequest.answer_value) when
    the question is a single_select/multi_select/numeric/yes_no/slider;
    display text (ChatRequest.message) is only used as a fallback for plain
    `text` questions. multi_select fields are always coerced to a list so
    they can never end up stored as a raw string (which would silently
    iterate character-by-character wherever the field is later used).
    """
    state = dict(state)
    field = question["field"]
    qtype = question.get("type")

    if qtype == "multi_select" and not isinstance(value, list):
        value = [v.strip() for v in str(value).split(",") if v.strip()]
    if qtype in ("numeric", "slider") and not isinstance(value, (int, float)):
        try:
            value = float(value)
        except (TypeError, ValueError):
            pass

    if field in ("age",):
        try:
            state["age"] = float(value)
        except (TypeError, ValueError):
            pass
        return state
    if field in ("sex", "pregnancy_status"):
        state[field] = value
        return state
    if field in ("medical_history", "medications", "allergies"):
        if isinstance(value, list):
            items = [str(v).strip() for v in value if str(v).strip()]
        else:
            items = [v.strip() for v in str(value).split(",") if v.strip()]
        if items and items[0].lower() not in ("none", "no", "n/a"):
            state[field] = items
        return state

    primary_name = state.get("primary_complaint")
    symptoms = list(state.get("symptoms", []))
    for i, s in enumerate(symptoms):
        if s.get("name") == primary_name:
            updated = dict(s)
            updated[field] = value
            symptoms[i] = updated
            break
    state["symptoms"] = symptoms
    return state
