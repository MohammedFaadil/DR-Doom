"""Regression tests for answer composition quality — the failures that made
early assessments unhelpful (thin/duplicated content, and care advice
borrowed from an unrelated condition)."""
import pytest

from app.agents.orchestrator import process_turn
# pyrefly: ignore [missing-import]
from app.agents.scope import classify_scope
from app.rag.index_manager import index_is_ready

pytestmark = pytest.mark.skipif(
    not index_is_ready(), reason="Knowledge base index not built — run scripts/ingest_documents.py first."
)


def _run_to_assessment(opening: str) -> str:
    state: dict = {}
    result = process_turn(state, opening, is_first_turn=True)
    state, question = result.state, result.question
    for _ in range(12):
        if question is None:
            break
        qid = question["id"]
        if qid == "age":
            value = 30
        elif qid == "sex":
            value = "female"
        elif qid == "pregnancy_status":
            value = "not_pregnant"
        elif "duration" in qid:
            value = "6-24h"
        elif question["type"] == "slider":
            value = 5
        else:
            value = "None"
        result = process_turn(state, str(value), answer_question=question, answer_value=value)
        state, question = result.state, result.question
        if result.response_type == "assessment":
            return result.message
    raise AssertionError("conversation never reached an assessment")


def test_fever_assessment_has_all_sections_and_real_content():
    message = _run_to_assessment("I have had a fever since last night")
    for heading in ("What I understand", "What this may mean", "What you can do now", "When to seek medical care"):
        assert f"## {heading}" in message
    # Real self-care content from the source, not the generic fallback.
    assert "My verified sources don't include specific self-care steps" not in message
    assert "medlineplus.gov/fever" in message


def test_fever_assessment_does_not_borrow_other_conditions_warnings():
    """Care/warning guidance must come from the condition being assessed —
    headache warning signs during a fever assessment are misleading."""
    message = _run_to_assessment("I have had a fever since last night")
    seek_section = message.split("## When to seek medical care")[1].split("**Sources**")[0]
    assert "headache" not in seek_section.lower()


def test_explanation_bullets_are_not_duplicated_labels():
    message = _run_to_assessment("I have had a fever since last night")
    means_section = message.split("## What this may mean")[1].split("## What you can do now")[0]
    bullet_labels = [line.split("**")[1] for line in means_section.splitlines() if line.startswith("- **")]
    assert len(bullet_labels) == len(set(bullet_labels)), f"duplicate bullet labels: {bullet_labels}"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("hi", "greeting"),
        ("hello there", "greeting"),
        ("what can you do?", "capability"),
        ("thanks", "gratitude"),
        ("write me a python script", "out_of_scope"),
        ("what's the weather today", "out_of_scope"),
        ("I have a headache", "medical"),
        ("what causes migraines?", "medical"),
    ],
)
def test_scope_classification(text, expected):
    assert classify_scope(text) == expected


@pytest.mark.parametrize(
    "opening,expected_source_fragment",
    [
        ("my stomach hurts", "Abdominal Pain"),
        ("my head hurts badly", "Headache"),
        ("I feel dizzy when I stand up", "Dizziness"),
    ],
)
def test_common_phrasings_reach_an_on_topic_assessment(opening, expected_source_fragment):
    """Regression: colloquial '<body part> hurts' phrasings were missing from
    the lexicon, and a hard domain filter in retrieval starved queries whose
    lexicon domain no document carries (dizziness matched only emergency
    docs, citing anaphylaxis and stroke)."""
    message = _run_to_assessment(opening)
    assert expected_source_fragment.lower() in message.lower()


def test_answering_a_question_does_not_drop_out_of_the_clinical_flow():
    """Regression: answering "28" to the age question re-classified the turn
    as a standalone factual question, aborting the assessment."""
    state: dict = {}
    result = process_turn(state, "my stomach hurts", is_first_turn=True)
    assert result.response_type == "question"
    state, question = result.state, result.question

    result = process_turn(state, "28", answer_question=question, answer_value=28)
    assert result.response_type == "question", "assessment flow was abandoned after a numeric answer"
    assert result.state["intent"] == "symptom_assessment"


def test_sources_are_not_duplicated():
    message = _run_to_assessment("I have a rash on my arm")
    sources = message.split("**Sources**")[1].strip().splitlines()
    urls = [line.split("](")[1].rstrip(")") for line in sources if "](" in line]
    assert len(urls) == len(set(urls)), f"duplicate source URLs: {urls}"


def test_greeting_gets_orientation_not_medical_refusal():
    result = process_turn({}, "hi", is_first_turn=True)
    assert result.response_type == "text"
    assert "don't have enough evidence" not in result.message
    assert "Dr Doom" in result.message


def test_out_of_scope_request_is_declined_helpfully():
    result = process_turn({}, "write me a poem about the sea", is_first_turn=True)
    assert result.response_type == "text"
    assert "health assistant" in result.message.lower()
