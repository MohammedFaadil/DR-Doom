from app.safety.emergency_engine import screen_for_emergency


def test_severe_chest_pain_with_radiation_triggers_emergency():
    matches = screen_for_emergency("I have severe chest pain radiating to my left arm and cold sweat")
    assert any(m.category == "cardiovascular" for m in matches)


def test_mild_chest_discomfort_alone_does_not_trigger_emergency():
    matches = screen_for_emergency(
        "I have mild chest pain", patient_state={"symptoms": [{"name": "chest pain", "severity": 3}]}
    )
    assert matches == []


def test_stroke_symptoms_trigger_emergency():
    matches = screen_for_emergency("My face is drooping on one side and my speech is slurred")
    assert any(m.category == "neurological" for m in matches)


def test_suicidal_ideation_triggers_mental_health_crisis():
    matches = screen_for_emergency("I want to end my life")
    assert any(m.category == "mental_health_crisis" for m in matches)


def test_anaphylaxis_keywords_trigger_emergency():
    matches = screen_for_emergency("My throat is swelling and I can't breathe after a bee sting")
    assert len(matches) >= 1


def test_ordinary_headache_does_not_trigger_emergency():
    matches = screen_for_emergency("I have a mild headache since this afternoon")
    assert matches == []


def test_pediatric_infant_fever_triggers_emergency():
    matches = screen_for_emergency(
        "My baby has a fever", patient_state={"age": 2, "age_unit": "months", "symptoms": [{"name": "fever"}]}
    )
    assert any(m.category == "pediatric" for m in matches)


def test_severe_bleeding_triggers_emergency():
    matches = screen_for_emergency("The bleeding won't stop from the cut")
    assert any(m.category == "trauma" for m in matches)
