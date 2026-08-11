"""
Semantic section classification for ingested chunks.

MedlinePlus content comes in two shapes and neither reliably carries the
labels we need for composing a structured clinical answer:

  * "structured" health topics carry question-style headings
    ("How are migraines treated?")
  * "flat" health topics (fever, headache, cough, chest pain, ... — roughly
    half the corpus) carry NO headings at all, just consecutive paragraphs

So rather than string-matching heading text at answer-composition time
(fragile, and impossible for flat docs), every chunk is classified once at
ingestion into a stable `section_category`. The composer
(app/agents/explanation.py) then asks for categories, not heading
substrings.

Classification is deterministic keyword scoring over the heading (weighted
heavily when present) plus the chunk body. It never invents content — it
only labels which part of an already-fetched source document a chunk is.
"""
from __future__ import annotations

# Ordered by specificity: the first category whose score wins ties should be
# the most actionable one, so "when_to_seek" beats generic "treatment".
CATEGORY_KEYWORDS: dict[str, tuple[tuple[str, int], ...]] = {
    "when_to_seek": (
        ("when to see", 6), ("when to call", 6), ("call your doctor", 6), ("call 911", 8),
        ("seek medical", 6), ("emergency", 4), ("get medical help", 8), ("right away", 4),
        ("warning sign", 5), ("see a doctor", 5), ("contact your", 3), ("immediately", 3),
        ("serious", 2), ("urgent", 3),
        # "Get immediate medical care if you have any of these" is the exact
        # phrasing MedlinePlus uses for its warning-sign lists on flat
        # (heading-less) pages like chest pain — without these it scores as
        # generic "treatment" and the warning list never reaches the
        # "When to seek medical care" section of the answer.
        ("immediate medical care", 10), ("get immediate", 8), ("medical care if", 8),
        ("go to the emergency", 10), ("doctor's attention", 6), ("emergency room", 8),
    ),
    "treatment": (
        ("treated", 6), ("treatment", 6), ("how is it treated", 8), ("therapy", 3),
        ("self-care", 6), ("home care", 6), ("relieve", 3), ("manage", 3), ("management", 3),
        ("medicine", 2), ("medication", 2), ("take an over-the-counter", 4), ("rest", 2),
        ("drink enough", 3), ("what can i do", 6), ("feel better", 3),
    ),
    "prevention": (
        ("prevent", 6), ("prevention", 6), ("avoid", 3), ("vaccine", 3), ("vaccinat", 3),
        ("reduce your risk", 5), ("lower your risk", 5),
    ),
    "symptoms": (
        ("symptom", 6), ("signs of", 4), ("what does it feel", 5), ("you may have", 2),
        ("you may feel", 2), ("common signs", 4),
    ),
    "causes": (
        ("cause", 6), ("causes", 6), ("what causes", 8), ("triggers", 4), ("trigger", 3),
        ("why does", 4), ("happens when", 3), ("due to", 2), ("result of", 2),
    ),
    "risk": (
        ("who is at risk", 10), ("risk factor", 6), ("at risk for", 5), ("more likely to get", 3),
    ),
    "diagnosis": (
        ("diagnos", 6), ("test", 3), ("exam", 2), ("how is it found", 5),
    ),
    "overview": (
        ("what is", 5), ("what are", 5), ("overview", 5), ("is a", 1), ("definition", 4),
    ),
    # --- drug-info specific ---
    "medication_uses": (
        ("why is this medication prescribed", 10), ("other uses for this medicine", 8),
        ("is used to", 4), ("used to relieve", 4), ("used to treat", 4),
    ),
    "medication_dosing": (
        ("how should this medicine be used", 10), ("comes as a", 3), ("take it at around the same", 4),
        ("follow the directions", 4), ("what should i do if i forget a dose", 10),
    ),
    "medication_precautions": (
        ("what special precautions should i follow", 10), ("important warning", 10),
        ("before taking", 6), ("tell your doctor", 4), ("should not take", 5),
        ("what special dietary", 8),
    ),
    "medication_side_effects": (
        ("what side effects can this medication cause", 10), ("side effect", 6), ("adverse", 4),
    ),
    "medication_overdose": (
        ("in case of emergency", 10), ("overdose", 8), ("poison control", 6),
    ),
    "medication_storage": (
        ("what should i know about storage", 10), ("store", 3), ("dispose", 3), ("keep this medication", 4),
    ),
}

TOPIC_CATEGORY_ORDER = [
    "overview",
    "causes",
    "symptoms",
    "risk",
    "diagnosis",
    "treatment",
    "when_to_seek",
    "prevention",
]

MEDICATION_CATEGORIES = {
    "medication_uses",
    "medication_dosing",
    "medication_precautions",
    "medication_side_effects",
    "medication_overdose",
    "medication_storage",
}


def classify_section(heading: str, text: str, source_type: str = "health_topic") -> str:
    """Return the best-matching `section_category` for a chunk.

    Heading matches are weighted 3x because an explicit heading like "How
    are migraines treated?" is far stronger evidence than the same words
    appearing incidentally in body prose.
    """
    heading_l = (heading or "").lower()
    text_l = (text or "").lower()[:1200]

    candidates = MEDICATION_CATEGORIES if source_type == "drug_info" else set(TOPIC_CATEGORY_ORDER)

    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category not in candidates:
            continue
        score = 0
        for kw, weight in keywords:
            if kw in heading_l:
                score += weight * 3
            if kw in text_l:
                score += weight
        if score:
            scores[category] = score

    if not scores:
        return "medication_uses" if source_type == "drug_info" else "overview"
    return max(scores.items(), key=lambda kv: kv[1])[0]


_LABELS = {
    "overview": "Overview",
    "causes": "Causes",
    "symptoms": "Symptoms",
    "risk": "Who is at risk",
    "diagnosis": "Diagnosis",
    "treatment": "Treatment & self-care",
    "when_to_seek": "When to seek care",
    "prevention": "Prevention",
    "medication_uses": "What it's used for",
    "medication_dosing": "How it's taken",
    "medication_precautions": "Precautions",
    "medication_side_effects": "Side effects",
    "medication_overdose": "Overdose / emergency",
    "medication_storage": "Storage",
}


def category_label(category: str) -> str:
    return _LABELS.get(category, category.replace("_", " ").title())
