from app.clinical.symptom_lexicon import extract_symptoms


def test_extracts_chest_pain():
    found = extract_symptoms("I have chest pain and shortness of breath")
    names = {s.canonical for s in found}
    assert "chest pain" in names
    assert "shortness of breath" in names


def test_extracts_nothing_from_unrelated_text():
    found = extract_symptoms("What is the capital of France?")
    assert found == []


def test_extracts_headache_synonym():
    found = extract_symptoms("I've had a migraine since yesterday")
    names = {s.canonical for s in found}
    assert "headache" in names
