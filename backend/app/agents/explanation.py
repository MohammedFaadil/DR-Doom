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


def _heading_count(text: str) -> int:
    return sum(1 for line in text.split("\n") if line.strip().startswith("## "))


# Shared by both compose_factual_answer and compose_assessment: the
# strict grounded-RAG contract handed to Groq (the only provider capable
# of full generation — see model_registry.py). {evidence_block} is filled
# in per call. GroundingValidator still re-checks the output afterward
# regardless — this prompt lowers how often that safety net has to catch
# something, it isn't trusted as the only line of defense.
_GROQ_SYSTEM_PROMPT_TEMPLATE = (
    "You are Dr Doom, an evidence-grounded health information assistant embedded in a "
    "consultation app. You are NOT a doctor and must never claim to be one or issue a diagnosis.\n\n"
    "You will be given RETRIEVED EVIDENCE below, and — as prior chat turns — the conversation "
    "so far with this patient. Answer using ONLY the RETRIEVED EVIDENCE as your source of "
    "medical facts. Use the conversation history only for context (what the patient already "
    "told you, what's already been discussed) — never as a source of new medical claims.\n\n"
    "STRICT RULES:\n"
    "1. Every medical fact, cause, symptom, drug name, or recommendation in your answer must be "
    "directly supported by the RETRIEVED EVIDENCE below. If the evidence doesn't cover something, "
    "say so plainly rather than filling the gap from general knowledge.\n"
    "2. Never name a specific serious condition (e.g. stroke, heart attack, cancer, tumor) unless "
    "that exact condition is explicitly present in the RETRIEVED EVIDENCE.\n"
    "3. Never give a diagnosis. Frame possible explanations as possibilities, and say plainly this "
    "is not a confirmed diagnosis.\n"
    "4. Reference the conversation history to stay consistent and specific to this patient — don't "
    "ask them to repeat information they already gave you, and don't contradict an earlier turn.\n"
    "5. Do not include a \"Sources\"/citations section yourself — the app appends real citations "
    "automatically after your answer.\n"
    "6. Write in clear, warm, plain language, not clinical jargon.\n"
    "7. Output ONLY the answer itself — no meta-commentary about what you're doing, no preamble "
    "like \"Here's my answer\", no closing summary of your own.\n"
    "8. If the RETRIEVED EVIDENCE is empty or clearly insufficient to answer safely, respond with "
    "exactly this sentence and nothing else: "
    '"I don\'t have enough evidence in my verified medical knowledge base to answer that safely."\n\n'
    "RETRIEVED EVIDENCE:\n{evidence_block}"
)

_MAX_HISTORY_MESSAGE_CHARS = 600


def _format_evidence_block(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no evidence retrieved)"
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[{i}] {_clean_title(c.chunk.title)} ({c.chunk.organization}) — "
            f"{category_label(c.chunk.section_category)}\n"
            f"{_trim(c.chunk.text, max_sentences=6, max_chars=700)}"
        )
    return "\n\n".join(parts)


def _recent_history(history: list[dict] | None) -> list[dict]:
    """`history` is prior conversation turns as {"role": "user"|"assistant",
    "content": str} dicts, oldest first — caller (app/api/chat.py) is
    responsible for windowing to CONVERSATION_HISTORY_TURNS. Each message
    is defensively length-capped here too, so one unusually long past
    assessment can't blow up prompt size."""
    if not history:
        return []
    out = []
    for h in history:
        role = h.get("role")
        content = (h.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        out.append({"role": role, "content": content[:_MAX_HISTORY_MESSAGE_CHARS]})
    return out


def _generate_grounded(
    task_instruction: str,
    evidence_chunks: list[RetrievedChunk],
    history: list[dict] | None,
    fallback_composed: str,
    top_for_grounding: list[RetrievedChunk],
) -> tuple[str, GroundingResult, str]:
    """Try full evidence+history-grounded generation (Groq) first; fall
    back to the existing deterministic-compose-then-rephrase path for
    every other provider, or if Groq is unavailable/fails/under-delivers.
    See `_rephrase_or_fallback` for why "under-delivers" (dropped
    sections, drastically shorter output) is checked the same way here as
    it is there — a capable model can still stop early on a long
    multi-section task, and that's not safe to show as-is.
    """
    manager = get_model_manager()
    if manager.supports_full_generation():
        system_prompt = _GROQ_SYSTEM_PROMPT_TEMPLATE.format(evidence_block=_format_evidence_block(evidence_chunks))
        messages = _recent_history(history) + [{"role": "user", "content": task_instruction}]
        raw = manager.generate_answer(system_prompt, messages)
        if raw:
            grounding = validate_grounding(raw, top_for_grounding)
            lost_sections = _heading_count(grounding.grounded_text) < _heading_count(fallback_composed)
            lost_most_content = len(grounding.grounded_text) < 0.5 * len(raw)
            if grounding.grounded_text and not lost_sections and not lost_most_content:
                return grounding.grounded_text, grounding, "groq"
    return _rephrase_or_fallback(fallback_composed, top_for_grounding)


def _rephrase_or_fallback(composed: str, top: list[RetrievedChunk]) -> tuple[str, GroundingResult, str]:
    """Rephrase via the active model provider, then validate grounding —
    but a small local model asked to rewrite a long multi-section note has
    a real, observed failure mode of stopping early (producing only the
    first section) rather than fabricating or refusing outright. That
    passes grounding validation just fine (what little it wrote is
    accurate) while silently discarding most of the answer, which is its
    own kind of unsafe for a medical app. Detect that here — heading count
    dropping, or the grounded text shrinking drastically — and fall back
    to the original composed text, which is safe by construction (built
    directly from retrieved evidence) and re-validated the same way rather
    than trusted blindly.
    """
    manager = get_model_manager()
    rephrased, provider = manager.rephrase(composed)
    grounding = validate_grounding(rephrased, top)

    is_real_rephrase = provider not in ("template", "template_fallback")
    lost_sections = is_real_rephrase and _heading_count(grounding.grounded_text) < _heading_count(composed)
    lost_most_content = is_real_rephrase and len(grounding.grounded_text) < 0.5 * len(composed)

    if not grounding.grounded_text or lost_sections or lost_most_content:
        fallback_grounding = validate_grounding(composed, top)
        return fallback_grounding.grounded_text or composed, fallback_grounding, "template_fallback"
    return grounding.grounded_text, grounding, provider


def compose_factual_answer(
    retrieval: RetrievalResult, user_text: str = "", history: list[dict] | None = None
) -> ExplanationOutput:
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
    cited = unique_docs[: len(body_parts)]

    task_instruction = (
        f'The patient just asked: "{user_text}"\n\n'
        "Answer it directly and completely using only the RETRIEVED EVIDENCE. Write 2-4 short "
        "plain-language paragraphs (no markdown headings needed for a direct question like this)."
    )
    final, grounding, provider = _generate_grounded(task_instruction, cited, history, body, top)
    final = final or INSUFFICIENT_EVIDENCE_MESSAGE

    message = f"{final}\n\n" + _sources_block(cited)
    return ExplanationOutput(message, cited, grounding, provider)


def compose_assessment(state: dict, retrieval: RetrievalResult, history: list[dict] | None = None) -> ExplanationOutput:
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
    cited = explain_chunks + care_chunks + warning_chunks

    task_instruction = (
        f"{_render_understanding(state)}\n\n"
        "Write a full patient-facing assessment using only the RETRIEVED EVIDENCE, with exactly "
        "these four markdown headings in this order — do not add, remove, rename, or reorder them, "
        "and do not add any other heading:\n"
        "## What I understand\n"
        "## What this may mean\n"
        "## What you can do now\n"
        "## When to seek medical care\n\n"
        "\"What I understand\" should restate the patient's own reported symptoms/profile above — "
        "not new evidence-derived content. \"What this may mean\" lists possible explanations from "
        "the evidence, explicitly not a diagnosis. \"What you can do now\" and \"When to seek "
        "medical care\" must come only from evidence about this same condition — if the evidence "
        "doesn't cover self-care or warning signs for it, say so rather than guessing."
    )
    final, grounding, provider = _generate_grounded(task_instruction, cited, history, composed, top)
    final = final or composed
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
