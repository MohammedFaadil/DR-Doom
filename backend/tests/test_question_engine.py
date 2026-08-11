from app.agents.intake import apply_intake
from app.agents.question import MAX_QUESTIONS, apply_answer, record_question_asked, select_next_question


def test_no_question_for_factual_intent():
    state = apply_intake({}, "What causes headaches?")
    assert state["intent"] == "factual_question"
    assert select_next_question(state) is None


def test_symptom_assessment_asks_associated_symptoms_first():
    state = apply_intake({}, "I have chest pain since this morning")
    q = select_next_question(state)
    assert q is not None
    assert q["clinical_priority"] == 1  # red-flag/associated-symptom question comes first


def test_question_loop_terminates_within_max_questions():
    state = apply_intake({}, "I have a headache")
    asked = 0
    while asked < MAX_QUESTIONS + 5:
        q = select_next_question(state)
        if q is None:
            break
        state = apply_answer(state, q, "none" if q["type"] == "multi_select" else "1")
        state = record_question_asked(state, q["id"])
        asked += 1
    assert asked <= MAX_QUESTIONS


def test_pregnancy_question_skipped_for_male():
    state = apply_intake({}, "I have a headache")
    state["sex"] = "male"
    state = record_question_asked(state, "age")
    state["age"] = 30
    q = select_next_question(state)
    assert q is None or q["id"] != "pregnancy_status"


def test_multi_select_answer_stored_as_list():
    state = apply_intake({}, "I have a headache")
    q = select_next_question(state)  # headache_associated, multi_select
    state = apply_answer(state, q, ["none"])
    symptom = next(s for s in state["symptoms"] if s["name"] == "headache")
    assert symptom["associated_symptoms"] == ["none"]
