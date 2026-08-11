"""
Medical terminology normalization / query rewriting (§87).

Purely a vocabulary mapping layer — it rewrites lay phrasing into the
clinical terms used by the knowledge base so retrieval finds the right
documents. It NEVER concludes a diagnosis; that distinction matters and is
enforced by keeping this module free of any risk/urgency logic (that lives
in app/safety/emergency_engine.py instead).
"""
from __future__ import annotations

import re

# lay phrase -> clinical/retrieval term. Longest phrases first so multi-word
# matches win over single-word substrings.
SYNONYM_MAP: dict[str, str] = {
    "heart racing": "palpitations",
    "heart pounding": "palpitations",
    "heart fluttering": "palpitations",
    "skipping heartbeats": "palpitations",
    "burning chest after eating": "GERD reflux",
    "burning in chest after meals": "GERD reflux",
    "acid coming up": "GERD reflux",
    "heartburn": "GERD reflux",
    "throwing up": "vomiting",
    "can't keep food down": "vomiting",
    "the runs": "diarrhea",
    "loose motions": "diarrhea",
    "can't poop": "constipation",
    "stomach ache": "abdominal pain",
    "tummy ache": "abdominal pain",
    "belly pain": "abdominal pain",
    "world spinning": "vertigo dizziness",
    "room spinning": "vertigo dizziness",
    "light headed": "dizziness",
    "lightheaded": "dizziness",
    "seeing spots": "vision changes",
    "blurry vision": "vision changes",
    "out of breath": "shortness of breath",
    "can't breathe": "shortness of breath",
    "short of breath": "shortness of breath",
    "winded": "shortness of breath",
    "pins and needles": "numbness tingling",
    "throbbing head": "headache",
    "splitting headache": "severe headache",
    "worst headache of my life": "thunderclap headache stroke",
    "face drooping": "stroke facial droop",
    "slurred speech": "stroke speech difficulty",
    "can't move my arm": "weakness stroke",
    "period pain": "menstrual cramps",
    "missed my period": "menstrual irregularity",
    "morning sickness": "pregnancy nausea",
    "can't sleep": "insomnia sleep problems",
    "feeling down": "low mood depression",
    "panic attack": "anxiety panic",
    "hives": "urticaria allergic reaction",
    "swollen throat": "anaphylaxis allergic reaction",
    "passed out": "syncope loss of consciousness",
    "blacked out": "syncope loss of consciousness",
    "high temperature": "fever",
    "running a fever": "fever",
    "runny nose": "common cold allergy",
    "stuffy nose": "common cold allergy",
    "sore muscles": "muscle pain",
    "achy joints": "joint pain",
    "itchy skin": "rash dermatitis",
}

_PATTERNS = sorted(SYNONYM_MAP.items(), key=lambda kv: len(kv[0]), reverse=True)


def normalize_query(text: str) -> str:
    """Rewrite lay phrasing to clinical terms; returns the (possibly)
    expanded query used for retrieval. Original user text is preserved
    elsewhere for display — this function is retrieval-only."""
    lowered = text.lower()
    expansions: list[str] = []
    for phrase, clinical_term in _PATTERNS:
        if phrase in lowered:
            expansions.append(clinical_term)
    if not expansions:
        return text
    return f"{text} {' '.join(expansions)}"


_WORD_RE = re.compile(r"[a-zA-Z']+")


def expand_synonyms_list(text: str) -> list[str]:
    """Returns just the matched clinical terms (used for symptom extraction)."""
    lowered = text.lower()
    return [term for phrase, term in _PATTERNS if phrase in lowered]
