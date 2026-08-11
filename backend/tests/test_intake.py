from app.agents.intake import apply_intake


def test_answer_label_does_not_spawn_new_top_level_symptom():
    """Regression test: selecting 'Severe headache' as a fever-associated
    symptom answer must not get misfiled as a brand-new 'headache'
    complaint — that caused assessments to blend unrelated topics."""
    state = apply_intake({}, "I have a fever since this morning")
    assert state["primary_complaint"] == "fever"

    # Simulate answering the associated-symptoms question with "Severe headache".
    state = apply_intake(state, "Severe headache", is_answer=True)

    names = [s["name"] for s in state["symptoms"]]
    assert names == ["fever"]
    assert state["primary_complaint"] == "fever"


def test_free_text_new_complaint_pivots_primary_complaint():
    state = apply_intake({}, "I have a fever")
    assert state["primary_complaint"] == "fever"

    state = apply_intake(state, "actually I'm having stomach pain now")
    assert state["primary_complaint"] == "abdominal pain"
    names = {s["name"] for s in state["symptoms"]}
    assert names == {"fever", "abdominal pain"}


def test_answer_never_pivots_primary_complaint():
    state = apply_intake({}, "I have a fever")
    state = apply_intake(state, "Difficulty breathing", is_answer=True)
    assert state["primary_complaint"] == "fever"
