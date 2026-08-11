"""
Deterministic symptom vocabulary used for extraction from free text.

This is intentionally simple keyword/synonym matching, not an ML classifier
— it is used to populate structured `patient_state.symptoms` and to decide
which question bank / retrieval domain applies. It carries no diagnostic
weight by itself; that separation is what keeps §17 ("Evidence -> Clinical
interpretation -> Explanation") true.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SymptomDef:
    canonical: str
    domain: str
    synonyms: tuple[str, ...]
    question_set: str  # key into app/clinical/question_bank/*.json


SYMPTOMS: list[SymptomDef] = [
    # "<body part> hurts/aches" is one of the most common ways people
    # actually describe a symptom, so each entry carries those forms
    # alongside the clinical term.
    SymptomDef("chest pain", "cardiovascular", ("chest pain", "chest tightness", "chest pressure", "chest discomfort", "chest hurts", "chest aches"), "chest_pain"),
    SymptomDef("palpitations", "cardiovascular", ("palpitations", "heart racing", "heart pounding", "irregular heartbeat"), "palpitations"),
    SymptomDef("headache", "general", ("headache", "head pain", "migraine", "head hurts", "head aches"), "headache"),
    SymptomDef("fever", "general", ("fever", "high temperature", "running a temperature", "chills"), "fever"),
    SymptomDef("cough", "respiratory", ("cough", "coughing"), "cough"),
    SymptomDef("shortness of breath", "respiratory", ("shortness of breath", "breathless", "can't breathe", "difficulty breathing", "trouble breathing"), "breathing"),
    SymptomDef("sore throat", "respiratory", ("sore throat", "throat pain", "painful swallowing", "throat hurts", "throat is sore"), "sore_throat"),
    SymptomDef(
        "abdominal pain",
        "gastrointestinal",
        (
            "abdominal pain", "stomach ache", "stomach pain", "belly pain", "tummy ache",
            "stomach hurts", "stomach aches", "belly hurts", "tummy hurts", "abdomen hurts",
            "stomach cramps", "stomach is hurting", "pain in my stomach", "pain in my abdomen",
        ),
        "abdominal_pain",
    ),
    SymptomDef("nausea", "gastrointestinal", ("nausea", "feeling sick", "queasy"), "nausea_vomiting"),
    SymptomDef("vomiting", "gastrointestinal", ("vomiting", "throwing up", "being sick"), "nausea_vomiting"),
    SymptomDef("diarrhea", "gastrointestinal", ("diarrhea", "diarrhoea", "loose stools", "the runs"), "diarrhea"),
    SymptomDef("constipation", "gastrointestinal", ("constipation", "can't poop", "not passing stool"), "constipation"),
    SymptomDef("dizziness", "neurological", ("dizziness", "dizzy", "lightheaded", "light headed", "vertigo", "room spinning"), "dizziness"),
    SymptomDef("back pain", "musculoskeletal", ("back pain", "backache", "back hurts", "back aches"), "back_pain"),
    SymptomDef("joint pain", "musculoskeletal", ("joint pain", "achy joints", "arthralgia", "joints hurt", "joints ache"), "joint_pain"),
    SymptomDef("muscle pain", "musculoskeletal", ("muscle pain", "muscle ache", "sore muscles", "myalgia"), "muscle_pain"),
    SymptomDef("rash", "dermatology", ("rash", "skin rash", "hives", "itchy skin", "spots on skin"), "rash"),
    SymptomDef("fatigue", "general", ("fatigue", "tired all the time", "exhausted", "low energy"), "fatigue"),
    SymptomDef("anxiety", "mental_health", ("anxious", "anxiety", "panic attack", "on edge"), "anxiety"),
    SymptomDef("low mood", "mental_health", ("depressed", "low mood", "feeling down", "hopeless"), "low_mood"),
    SymptomDef("sleep problems", "mental_health", ("can't sleep", "insomnia", "trouble sleeping"), "sleep"),
    SymptomDef("menstrual symptoms", "womens_health", ("period pain", "menstrual cramps", "missed period", "heavy periods"), "menstrual"),
    SymptomDef("testicular pain", "mens_health", ("testicular pain", "testicle pain", "groin pain in men"), "testicular_pain"),
    SymptomDef("seizure", "emergency", ("seizure", "fit", "convulsion"), "seizure"),
    SymptomDef("severe allergic reaction", "emergency", ("swollen throat", "throat closing", "anaphylaxis", "face swelling after"), "allergic_reaction"),
    SymptomDef("loss of consciousness", "emergency", ("passed out", "blacked out", "fainted", "loss of consciousness"), "loss_of_consciousness"),
    SymptomDef("stroke symptoms", "emergency", ("face drooping", "slurred speech", "sudden weakness one side", "can't move my arm"), "stroke_symptoms"),
]

def _phrase_pattern(phrase: str) -> re.Pattern:
    """Build a regex for a synonym phrase that also matches its words in
    reversed order a short distance apart — e.g. the synonym "sore throat"
    should still match "my throat has been sore for two days", not just the
    exact adjacent phrase. Single-word synonyms match as plain word-boundary
    literals; longer (3+ word) synonyms are matched as an exact phrase since
    reordering those tends to change the meaning."""
    words = phrase.split()
    if len(words) != 2:
        return re.compile(r"\b" + re.escape(phrase) + r"\b")
    w1, w2 = (re.escape(w) for w in words)
    gap = r"(?:\W+\w+){0,3}\W+"
    return re.compile(rf"\b{w1}\b{gap}\b{w2}\b|\b{w2}\b{gap}\b{w1}\b|\b{w1}\W+{w2}\b")


_LOOKUP: list[tuple[re.Pattern, SymptomDef]] = [
    (_phrase_pattern(s), sd) for sd in SYMPTOMS for s in sd.synonyms
]


def extract_symptoms(text: str) -> list[SymptomDef]:
    lowered = text.lower()
    found: dict[str, SymptomDef] = {}
    for pattern, sd in _LOOKUP:
        if pattern.search(lowered):
            found[sd.canonical] = sd
    return list(found.values())


def get_symptom(canonical: str) -> SymptomDef | None:
    for sd in SYMPTOMS:
        if sd.canonical == canonical:
            return sd
    return None
