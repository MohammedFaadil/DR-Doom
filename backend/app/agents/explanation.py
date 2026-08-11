"""
Clinical Explanation Agent (§17, §52.5, §64).

Builds the response deterministically from structured patient state +
retrieved evidence (Evidence -> Clinical interpretation -> Explanation),
then optionally asks the ModelManager to rephrase it in plainer language,
then always re-validates the final text with the GroundingValidator before
it is returned. Response shape follows §64:
  simple factual question -> answer directly
  symptom assessment       -> full structured sections
  insufficient evidence    -> §48 fallback message, no fabricated content

Sections are assembled from chunks' `section_category` (see
app/rag/sections.py) rather than by string-matching heading text, because
roughly half the source documents carry no headings at all. Each section
draws from the best-scoring chunk of the matching category, so "What you
can do now" gets real self-care content and "When to seek medical care"
gets real warning signs — instead of both falling back to boilerplate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.clinical.symptom_lexicon import get_symptom
from app.core.model_manager import get_model_manager
from app.rag.hybrid import RetrievalResult
from app.rag.sections import category_label
from app.rag.types import RetrievedChunk
from app.safety.grounding_validator import GroundingResult, validate_grounding

MIN_RETRIEVAL_SCORE_FOR_ANSWER = 0.30

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I don't have enough evidence in my verified medical knowledge base to answer that safely. "
    "Would you like to ask about a different health concern?"
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# What a patient actually needs to know first, in order. A bare definition
# ("a fever is a temperature higher than normal") is the least useful thing
# we can lead with, so it ranks last.
_EXPLAIN_PRIORITY = {"causes": 0, "symptoms": 1, "risk": 2, "overview": 3}
# MedlinePlus flattens <li> items into prose, leaving runs like
# "Chronic bronchitis Asthma Allergies COPD" — detectable by a lack of
# sentence punctuation across a long span.
_LIST_LEAD_IN = re.compile(r":\s*$")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if s.strip()]


def _trim(text: str, max_sentences: int, max_chars: int) -> str:
    """Keep a chunk readable: at most `max_sentences`, and never a partial
    sentence — we cut at a sentence boundary rather than mid-clause so the
    displayed text is always grammatical and never changes meaning."""
    kept: list[str] = []
    length = 0
    for s in _sentences(text)[:max_sentences]:
        if kept and length + len(s) > max_chars:
            break
        kept.append(s)
        length += len(s) + 1
    return " ".join(kept) if kept else text[:max_chars].rstrip()


@dataclass
class ExplanationOutput:
    message: str
    evidence: list[RetrievedChunk]
    grounding: GroundingResult
    model_provider: str


def _dedupe_by_doc(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[str] = set()
    out = []
    for c in chunks:
        if c.chunk.doc_id in seen:
            continue
        seen.add(c.chunk.doc_id)
        out.append(c)
    return out


def _dedupe_by_doc_section(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Dedupe on (document, section) rather than document alone.

    Deduping by document alone would collapse a topic's 'overview' and
    'causes' chunks into a single entry — losing the actually-informative
    one — because they come from the same source page.
    """
    seen: set[tuple[str, str]] = set()
    out = []
    for c in chunks:
        key = (c.chunk.doc_id, c.chunk.section_category)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _by_category(chunks: list[RetrievedChunk], categories: set[str]) -> list[RetrievedChunk]:
    return [c for c in chunks if c.chunk.section_category in categories]


def _topic_profile(state: dict) -> tuple[set[str], str | None]:
    """Words + medical domain identifying the primary complaint, used to
    keep an assessment focused on THAT complaint rather than other symptoms
    the retrieval query's associated-symptom terms also matched."""
    primary = state.get("primary_complaint")
    if not primary:
        return set(), None
    words = set(primary.lower().split())
    domain = None
    symptom_def = get_symptom(primary)
    if symptom_def:
        domain = symptom_def.domain
        for syn in symptom_def.synonyms:
            words.update(syn.lower().split())
    words -= {"of", "in", "the", "a", "on", "my"}
    return words, domain


def _is_same_condition(chunk: RetrievedChunk, topic_words: set[str]) -> bool:
    """Strict: this chunk's document is about the complaint itself.

    Used for care and warning guidance, where content from a *different*
    condition is actively misleading (headache warning signs shown during a
    fever assessment). Domain is deliberately NOT accepted here — most
    common symptoms share the catch-all "general" domain, so a domain match
    says almost nothing about whether the advice actually applies.
    """
    if not topic_words:
        return True
    title_words = set(re.findall(r"[a-z]+", chunk.chunk.title.lower()))
    return bool(topic_words & title_words)


def _is_related(chunk: RetrievedChunk, topic_words: set[str], domain: str | None) -> bool:
    """Looser: same condition, or the same clinical domain.

    Used only for the "what this may mean" section, where a related
    condition is legitimate context (a cough assessment surfacing pneumonia)
    and is explicitly framed as a possible explanation, not as advice.
    """
    if _is_same_condition(chunk, topic_words):
        return True
    return domain is not None and chunk.chunk.medical_domain == domain


def compose_factual_answer(retrieval: RetrievalResult) -> ExplanationOutput:
    top = [c for c in retrieval.chunks if c.rerank_score > 0]
    if not top or top[0].rerank_score < MIN_RETRIEVAL_SCORE_FOR_ANSWER:
        return ExplanationOutput(
            INSUFFICIENT_EVIDENCE_MESSAGE, [], GroundingResult(INSUFFICIENT_EVIDENCE_MESSAGE, 0.0), "template"
        )

    unique_docs = _dedupe_by_doc(top)[:3]
    lead = unique_docs[0]
    body_parts = [_trim(lead.chunk.text, max_sentences=4, max_chars=520)]

    # Add one complementary angle (a different section of the same or a
    # related topic) so a direct question gets a rounded answer, not just
    # the single best-matching paragraph.
    for c in unique_docs[1:]:
        if c.chunk.section_category != lead.chunk.section_category:
            body_parts.append(_trim(c.chunk.text, max_sentences=3, max_chars=380))
            break

    body = "\n\n".join(body_parts)

    manager = get_model_manager()
    rephrased, provider = manager.rephrase(body)
    grounding = validate_grounding(rephrased, top)
    final = grounding.grounded_text or INSUFFICIENT_EVIDENCE_MESSAGE

    cited = unique_docs[: len(body_parts)]
    message = f"{final}\n\n" + _sources_block(cited)
    return ExplanationOutput(message, cited, grounding, provider)


def compose_assessment(state: dict, retrieval: RetrievalResult) -> ExplanationOutput:
    top = [c for c in retrieval.chunks if c.rerank_score > 0]
    if not top or top[0].rerank_score < MIN_RETRIEVAL_SCORE_FOR_ANSWER:
        return ExplanationOutput(
            INSUFFICIENT_EVIDENCE_MESSAGE, [], GroundingResult(INSUFFICIENT_EVIDENCE_MESSAGE, 0.0), "template"
        )

    topic_words, domain = _topic_profile(state)
    same_condition = [c for c in top if _is_same_condition(c, topic_words)]
    related = [c for c in top if _is_related(c, topic_words, domain)]

    # Explanation may fall back to the wider result set if nothing matched
    # the complaint by name/domain — a related topic is still informative
    # context there, and it's clearly framed as "possible explanations".
    explain_pool = related or top
    explain_chunks = _dedupe_by_doc_section(
        # Causes/symptoms are far more useful to a patient than a dictionary
        # definition, so order the pool by usefulness before taking the top 2.
        sorted(
            _by_category(explain_pool, {"overview", "causes", "symptoms", "risk"}) or explain_pool,
            key=lambda c: _EXPLAIN_PRIORITY.get(c.chunk.section_category, 9),
        )
    )[:2]

    # Care and warning guidance is NEVER borrowed from another condition —
    # showing headache warning signs during a fever assessment is actively
    # misleading, so these fall back to safe generic text instead.
    care_chunks = _dedupe_by_doc_section(_by_category(same_condition, {"treatment", "prevention"}))[:2]
    warning_chunks = _dedupe_by_doc_section(_by_category(same_condition, {"when_to_seek"}))[:2]

    sections = [
        "## What I understand",
        _render_understanding(state),
        "## What this may mean",
        _render_possible_causes(explain_chunks),
        "## What you can do now",
        _render_bullets(
            care_chunks,
            fallback="- My verified sources don't include specific self-care steps for this. A clinician can advise on what's appropriate for your situation.",
        ),
        "## When to seek medical care",
        _render_bullets(
            warning_chunks,
            fallback="- Seek medical evaluation if symptoms get worse, don't improve, or you develop any new or severe symptoms.",
        ),
    ]
    composed = "\n\n".join(sections)

    manager = get_model_manager()
    rephrased, provider = manager.rephrase(composed)
    grounding = validate_grounding(rephrased, top)
    final = grounding.grounded_text or composed

    cited = explain_chunks + care_chunks + warning_chunks
    message = f"{final}\n\n" + _sources_block(cited)
    return ExplanationOutput(message, _dedupe_by_doc(cited), grounding, provider)


def _render_possible_causes(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return (
            "*This is not a confirmed diagnosis.* My verified sources don't contain enough detail "
            "to suggest possible explanations here."
        )
    lines = ["*These are possible explanations from my verified sources — not a confirmed diagnosis.*", ""]
    # When both bullets come from the same source document, labelling them
    # with the document title twice reads as a duplicate; label them by
    # which part of that document they came from instead.
    single_doc = len({c.chunk.doc_id for c in chunks}) == 1
    for c in chunks:
        label = category_label(c.chunk.section_category) if single_doc else c.chunk.title
        lines.append(f"- **{label}** — {_trim(c.chunk.text, max_sentences=3, max_chars=420)}")
    return "\n".join(lines)


def _render_bullets(chunks: list[RetrievedChunk], fallback: str) -> str:
    if not chunks:
        return fallback
    return "\n".join(f"- {_trim(c.chunk.text, max_sentences=3, max_chars=420)}" for c in chunks)


def _render_understanding(state: dict) -> str:
    primary = state.get("primary_complaint", "your symptoms")
    detail_bits: list[str] = []
    associated: list[str] = []

    for s in state.get("symptoms", []):
        if s.get("name") != primary:
            continue
        if s.get("duration"):
            detail_bits.append(f"duration {s['duration']}")
        if s.get("severity") is not None:
            detail_bits.append(f"severity {s['severity']}/10")
        if s.get("location"):
            detail_bits.append(f"location {str(s['location']).replace('_', ' ')}")
        if s.get("onset_pattern"):
            detail_bits.append(f"onset {str(s['onset_pattern']).replace('_', ' ')}")
        for a in s.get("associated_symptoms") or []:
            label = str(a).replace("_", " ")
            if label.lower() not in ("none", "none of these"):
                associated.append(label)
        break

    line = f"You reported **{primary}**"
    if detail_bits:
        line += f" ({', '.join(detail_bits)})"
    line += "."

    parts = [line]
    if associated:
        parts.append(f"Also reported alongside it: {', '.join(associated)}.")

    profile_bits = []
    if state.get("age") is not None:
        age = state["age"]
        unit = "months" if state.get("age_unit") == "months" else "years"
        profile_bits.append(f"{int(age)} {unit}")
    if state.get("sex") and state["sex"] != "prefer_not_to_say":
        profile_bits.append(str(state["sex"]))
    if profile_bits:
        parts.append(f"Profile considered: {', '.join(profile_bits)}.")

    return " ".join(parts)


def _sources_block(chunks: list[RetrievedChunk]) -> str:
    # Dedupe by URL, not doc_id: two ingested topics can resolve to the same
    # MedlinePlus page (e.g. "rash" and "dermatitis" both land on Rashes),
    # which would otherwise render as a duplicated citation.
    seen: set[str] = set()
    lines = ["**Sources**"]
    index = 1
    for c in chunks:
        if c.chunk.url in seen:
            continue
        seen.add(c.chunk.url)
        lines.append(f"{index}. [{c.chunk.organization} — {_clean_title(c.chunk.title)}]({c.chunk.url})")
        index += 1
    return "\n".join(lines) if index > 1 else ""


def _clean_title(title: str) -> str:
    """MedlinePlus titles occasionally arrive with doubled internal spaces
    (e.g. "Sore  Throat") from the source markup."""
    return re.sub(r"\s+", " ", title).strip()
