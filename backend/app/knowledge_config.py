"""
Curated source manifest for knowledge ingestion.

This file lists WHAT to fetch (a query term + our own clinical tags) — it
contains no medical claims of its own. All actual medical content is fetched
live from MedlinePlus (National Library of Medicine / NIH) at ingestion time
by scripts/ingest_documents.py, so citations shown to users always resolve
to a real, authoritative source page.

Each topic maps to a MedlinePlus Web Service (wsearch) health-topic query.
Each drug maps to a name that scripts/ingest_documents.py resolves to a real
RxCUI via the RxNorm API, then to a real MedlinePlus Connect drug-info page.
If a lookup fails, the ingestion script skips it and logs a warning — it
never fabricates a substitute.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TopicSource:
    slug: str
    query: str
    medical_domain: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DrugSource:
    slug: str
    name: str
    drug_class: str


TOPICS: list[TopicSource] = [
    # --- General medicine ---
    TopicSource("fever", "fever", "general", ("common",)),
    TopicSource("headache", "headache", "general", ("common",)),
    TopicSource("migraine", "migraine", "general", ("common",)),
    TopicSource("cough", "cough", "respiratory", ("common",)),
    TopicSource("common-cold", "common cold", "respiratory", ("common",)),
    TopicSource("sore-throat", "sore throat", "respiratory", ("common",)),
    TopicSource("fatigue", "fatigue", "general", ("common",)),
    TopicSource("dizziness", "dizziness", "general", ("common", "elderly_relevant")),
    TopicSource("nausea-vomiting", "nausea and vomiting", "gastrointestinal", ("common",)),
    TopicSource("diarrhea", "diarrhea", "gastrointestinal", ("common",)),
    TopicSource("constipation", "constipation", "gastrointestinal", ("common",)),
    TopicSource("abdominal-pain", "abdominal pain", "gastrointestinal", ("common",)),
    TopicSource("back-pain", "back pain", "musculoskeletal", ("common",)),
    TopicSource("joint-pain", "joint pain", "musculoskeletal", ("common",)),
    TopicSource("muscle-pain", "muscle aches", "musculoskeletal", ("common",)),
    # --- Cardiovascular ---
    TopicSource("hypertension", "high blood pressure", "cardiovascular", ("chronic",)),
    TopicSource("chest-pain", "chest pain", "cardiovascular", ("emergency_related",)),
    TopicSource("palpitations", "heart palpitations", "cardiovascular", ("emergency_related",)),
    TopicSource("heart-attack", "heart attack", "cardiovascular", ("emergency_related",)),
    TopicSource("stroke", "stroke", "cardiovascular", ("emergency_related",)),
    # --- Respiratory ---
    TopicSource("asthma", "asthma", "respiratory", ("chronic", "pediatric_relevant")),
    TopicSource("copd", "COPD", "respiratory", ("chronic", "elderly_relevant")),
    TopicSource("pneumonia", "pneumonia", "respiratory", ("emergency_related",)),
    TopicSource("bronchitis", "bronchitis", "respiratory", ("common",)),
    TopicSource("allergies", "allergy", "respiratory", ("common",)),
    # --- Gastrointestinal ---
    TopicSource("gerd", "GERD", "gastrointestinal", ("chronic",)),
    TopicSource("gastritis", "gastritis", "gastrointestinal", ("common",)),
    TopicSource("ibs", "irritable bowel syndrome", "gastrointestinal", ("chronic",)),
    TopicSource("food-poisoning", "food poisoning", "gastrointestinal", ("common",)),
    # --- Dermatology ---
    TopicSource("rash", "skin rashes", "dermatology", ("common",)),
    TopicSource("acne", "acne", "dermatology", ("common",)),
    TopicSource("eczema", "eczema", "dermatology", ("chronic",)),
    TopicSource("dermatitis", "dermatitis", "dermatology", ("common",)),
    TopicSource("fungal-infections", "fungal infections", "dermatology", ("common",)),
    # --- Mental wellbeing ---
    TopicSource("stress", "stress", "mental_health", ("common",)),
    TopicSource("sleep-problems", "sleep disorders", "mental_health", ("common",)),
    TopicSource("anxiety", "anxiety", "mental_health", ("sensitive",)),
    TopicSource("depression", "depression", "mental_health", ("sensitive",)),
    # --- Women's health ---
    TopicSource("menstrual-health", "menstruation", "womens_health", ("womens_health",)),
    TopicSource("pregnancy-symptoms", "pregnancy symptoms", "womens_health", ("womens_health", "pregnancy_relevant")),
    TopicSource("pcos", "polycystic ovary syndrome", "womens_health", ("womens_health",)),
    TopicSource("menopause", "menopause", "womens_health", ("womens_health",)),
    # --- Men's health ---
    TopicSource("prostate", "prostate diseases", "mens_health", ("mens_health",)),
    TopicSource("sexual-health-men", "erectile dysfunction", "mens_health", ("mens_health", "sensitive")),
    TopicSource("testicular-disorders", "testicular disorders", "mens_health", ("mens_health", "emergency_related")),
    # --- Pediatrics ---
    TopicSource("fever-in-children", "fever in children", "pediatrics", ("pediatric_relevant",)),
    TopicSource("febrile-seizures", "febrile seizures", "pediatrics", ("pediatric_relevant", "emergency_related")),
    TopicSource("childhood-immunization", "child immunization schedule", "pediatrics", ("pediatric_relevant",)),
    # --- Elderly care ---
    TopicSource("falls-elderly", "falls in the elderly", "elderly_care", ("elderly_relevant",)),
    TopicSource("dementia", "dementia", "elderly_care", ("elderly_relevant",)),
    # --- Emergency-critical topics ---
    TopicSource("severe-allergic-reaction", "anaphylaxis", "emergency", ("emergency_related",)),
    TopicSource("seizures", "seizures", "emergency", ("emergency_related",)),
    TopicSource("poisoning", "poisoning", "emergency", ("emergency_related",)),
    TopicSource("severe-bleeding", "wounds and injuries bleeding", "emergency", ("emergency_related",)),
    TopicSource("suicide-crisis", "suicide and crisis intervention", "emergency", ("emergency_related", "sensitive")),
]

DRUGS: list[DrugSource] = [
    DrugSource("ibuprofen", "ibuprofen", "NSAID / pain reliever"),
    DrugSource("acetaminophen", "acetaminophen", "analgesic/antipyretic"),
    DrugSource("aspirin", "aspirin", "NSAID / antiplatelet"),
    DrugSource("amoxicillin", "amoxicillin", "antibiotic"),
    DrugSource("azithromycin", "azithromycin", "antibiotic"),
    DrugSource("loratadine", "loratadine", "antihistamine"),
    DrugSource("cetirizine", "cetirizine", "antihistamine"),
    DrugSource("diphenhydramine", "diphenhydramine", "antihistamine"),
    DrugSource("omeprazole", "omeprazole", "proton pump inhibitor"),
    DrugSource("famotidine", "famotidine", "H2 blocker"),
    DrugSource("loperamide", "loperamide", "antidiarrheal"),
    DrugSource("metformin", "metformin", "antidiabetic"),
    DrugSource("lisinopril", "lisinopril", "ACE inhibitor / antihypertensive"),
    DrugSource("amlodipine", "amlodipine", "calcium channel blocker / antihypertensive"),
    DrugSource("atorvastatin", "atorvastatin", "statin"),
    DrugSource("albuterol", "albuterol", "bronchodilator"),
    DrugSource("prednisone", "prednisone", "corticosteroid"),
    DrugSource("sertraline", "sertraline", "SSRI antidepressant"),
    DrugSource("levothyroxine", "levothyroxine", "thyroid hormone replacement"),
    DrugSource("metronidazole", "metronidazole", "antibiotic"),
]
