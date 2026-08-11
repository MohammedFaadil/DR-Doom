"""
GroundingValidator (§18).

response -> claim extraction (sentence split) -> evidence matching
(embedding similarity against retrieved chunks) -> unsupported claim
detection -> removal -> final answer.

This runs on EVERY generated response, regardless of which model provider
produced it (defense in depth — even the deterministic TemplateProvider
passes through this, though it should always pass since its text is built
directly from the evidence).

Structural lines (headings, disclaimers, citation lists, bullet labels) are
exempt from claim-checking — only substantive sentences are checked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from app.config import get_settings
from app.rag.embeddings import get_embedding_model
from app.rag.types import RetrievedChunk

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_EXEMPT_PREFIXES = ("#", "-", "*", "[", "**Sources", "**Disclaimer", "Disclaimer:")

_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
# Proper-noun-ish runs (e.g. "Jonathan Smith"), skipping the sentence's own
# first word since capitalization there is just normal sentence case.
_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")

# A rephrasing model asked to discuss "when to seek care" has an observed,
# repeatable failure mode: reaching for a scary-but-plausible serious
# condition ("...could be a sign of stroke, brain tumor...") that reads as
# reasonable caution but was never in the retrieved evidence — a topically
# "on-brand" fabrication that embedding similarity alone does not catch,
# since the sentence is still semantically close to the headache/care
# evidence it's embedded near. These are lowercase common nouns, so the
# proper-noun check above never sees them either. Checked the same way as
# proper nouns/years: only flagged if genuinely absent from every retrieved
# chunk, so a condition the evidence itself actually discusses is fine.
_HIGH_STAKES_TERMS = (
    "stroke", "brain tumor", "brain tumour", "aneurysm", "meningitis", "sepsis",
    "heart attack", "myocardial infarction", "cardiac arrest", "embolism",
    "hemorrhage", "haemorrhage", "internal bleeding", "organ failure", "blood clot",
    "malignant", "malignancy", "leukemia", "leukaemia", "tumor", "tumour",
)
_HIGH_STAKES_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in _HIGH_STAKES_TERMS) + r")\b", re.IGNORECASE)


def _unsupported_entities(sentence: str, evidence_text_lower: str) -> list[str]:
    """Cheap, deterministic entailment check layered on top of embedding
    similarity: specific names/years/high-stakes conditions asserted in a
    sentence but absent from every retrieved chunk are a strong fabrication
    signal that topic-level semantic similarity alone can miss (a sentence
    can be "about migraines" and still invent a person, date, or a scarier
    condition than what's actually supported)."""
    words = sentence.strip().split(" ", 1)
    rest = words[1] if len(words) > 1 else ""
    candidates = _PROPER_NOUN_RE.findall(rest) + _YEAR_RE.findall(sentence) + _HIGH_STAKES_RE.findall(sentence)
    return [c for c in candidates if c.lower() not in evidence_text_lower]


@dataclass
class GroundingResult:
    grounded_text: str
    confidence: float
    unsupported_sentences: list[str] = field(default_factory=list)
    checked_sentence_count: int = 0
    supported_sentence_count: int = 0


def _is_exempt(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith(_EXEMPT_PREFIXES):
        return True
    if len(stripped) < 12:
        return True
    return False


def validate_grounding(text: str, evidence: list[RetrievedChunk]) -> GroundingResult:
    settings = get_settings()
    if not evidence:
        # Nothing to ground against — caller (explanation agent) should have
        # already produced the "insufficient evidence" message instead of
        # reaching here with substantive claims.
        return GroundingResult(grounded_text=text, confidence=0.0)

    model = get_embedding_model()
    evidence_texts = [f"{c.chunk.section_heading}: {c.chunk.text}" for c in evidence]
    evidence_vectors = model.embed(evidence_texts)
    evidence_text_lower = " ".join(evidence_texts).lower()

    out_lines: list[str] = []
    unsupported: list[str] = []
    scores: list[float] = []

    for line in text.split("\n"):
        if _is_exempt(line):
            out_lines.append(line)
            continue

        sentences = [s for s in _SENTENCE_SPLIT.split(line) if s.strip()]
        kept_sentences: list[str] = []
        for sentence in sentences:
            if len(sentence.strip()) < 12:
                kept_sentences.append(sentence)
                continue
            vec = model.embed_one(sentence)
            sims = evidence_vectors @ vec
            best = float(np.max(sims)) if len(sims) else 0.0
            scores.append(best)
            stray_entities = _unsupported_entities(sentence, evidence_text_lower)
            if best >= settings.GROUNDING_MIN_SIMILARITY and not stray_entities:
                kept_sentences.append(sentence)
            else:
                unsupported.append(sentence.strip())
        if kept_sentences:
            out_lines.append(" ".join(kept_sentences))

    confidence = float(np.mean(scores)) if scores else 1.0
    return GroundingResult(
        grounded_text="\n".join(out_lines).strip(),
        confidence=confidence,
        unsupported_sentences=unsupported,
        checked_sentence_count=len(scores),
        supported_sentence_count=len(scores) - len(unsupported),
    )
