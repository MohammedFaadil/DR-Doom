"""
Medically-aware HTML chunking for ingested source documents.

Three real MedlinePlus HTML shapes are handled:

1. "Structured" health-topic FullSummary fragments (from the wsearch API):
   headings are bare text nodes immediately followed by a <p> — e.g.
   "What causes migraines?<p>...</p>". We walk the fragment's direct
   children and treat a run of bare text before a <p>/<ul> as the section
   heading for the content that follows.

2. "Flat" health-topic FullSummary fragments — roughly half the corpus
   (fever, headache, cough, chest pain, ...) has NO headings at all, just
   consecutive <p>/<ul> elements. Treating these as one giant "Overview"
   chunk made them effectively useless for retrieval (a query for fever
   treatment would only ever match one generic definition blob), so they
   are split into paragraph-group chunks instead and labelled by content.

3. Drug-info pages (medlineplus.gov/druginfo/meds/...): explicit
   `<div class="section">` blocks, each with an `<h2>`/`<h3>` heading and a
   `.section-body` container.

Every emitted chunk is classified into a stable `section_category` (see
app/rag/sections.py) so answer composition can ask for "the treatment part"
without string-matching heading text that may not exist at all.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

from app.rag.sections import classify_section

MAX_CHUNK_CHARS = 1200
MIN_CHUNK_CHARS = 40
# Flat docs: merge consecutive short paragraphs up to this size so a chunk
# carries enough context to be meaningful on its own, but stays focused.
FLAT_TARGET_CHARS = 550


@dataclass
class RawChunk:
    heading: str
    text: str
    category: str = "overview"


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def chunk_health_topic_summary(full_summary_html: str) -> list[RawChunk]:
    """Chunk a MedlinePlus health-topic FullSummary fragment.

    Uses heading-based sectioning when the document actually has headings,
    and falls back to paragraph-group chunking when it doesn't.
    """
    soup = BeautifulSoup(f"<div>{full_summary_html}</div>", "lxml")
    root = soup.div
    if root is None:
        return []

    blocks = _extract_blocks(root)
    has_headings = any(b[0] == "heading" for b in blocks)

    chunks = _chunk_with_headings(blocks) if has_headings else _chunk_flat(blocks)
    return [c for chunk in chunks for c in _split_chunk_if_long(chunk)]


def _extract_blocks(root: Tag) -> list[tuple[str, str]]:
    """Flatten the fragment into ('heading'|'p'|'list', text) blocks.

    Lists are tagged distinctly from paragraphs because a <ul> on these
    pages is almost always the payload of the sentence immediately before
    it ("Get medical help right away if:" followed by the warning list) —
    the two must never be split into different chunks or the list loses the
    context that gives it meaning.
    """
    blocks: list[tuple[str, str]] = []
    for node in root.children:
        if isinstance(node, NavigableString):
            text = _clean_text(str(node))
            if text:
                blocks.append(("heading", text))
        elif isinstance(node, Tag):
            if node.name in ("ul", "ol"):
                text = _clean_text(node.get_text(" "))
                if text:
                    blocks.append(("list", text))
            elif node.name == "p":
                text = _clean_text(node.get_text(" "))
                if text:
                    blocks.append(("p", text))
            elif node.name in ("h1", "h2", "h3", "h4"):
                text = _clean_text(node.get_text(" "))
                if text:
                    blocks.append(("heading", text))
            else:
                # Inline tags (span/strong/em/a) sitting at the top level are
                # part of the heading sentence preceding the next <p> —
                # e.g. "What are <span>migraines</span>?"
                text = _clean_text(node.get_text(" "))
                if text:
                    blocks.append(("heading", text))
    return blocks


def _chunk_with_headings(blocks: list[tuple[str, str]]) -> list[RawChunk]:
    chunks: list[RawChunk] = []
    heading_parts: list[str] = []
    body_parts: list[str] = []

    def flush() -> None:
        heading = _clean_text(" ".join(heading_parts)) or "Overview"
        body = _clean_text(" ".join(body_parts))
        if len(body) >= MIN_CHUNK_CHARS:
            chunks.append(RawChunk(heading=heading, text=body, category=classify_section(heading, body)))
        heading_parts.clear()
        body_parts.clear()

    for kind, text in blocks:
        if kind == "heading":
            if body_parts:
                flush()
            heading_parts.append(text)
        else:
            body_parts.append(text)
    flush()
    return chunks


def _can_break_before(prev_text: str, kind: str) -> bool:
    """A group must not end on a lead-in that introduces what follows."""
    if kind == "list":
        return False  # a list always belongs with the sentence before it
    return not prev_text.rstrip().endswith(":")


def _chunk_flat(blocks: list[tuple[str, str]]) -> list[RawChunk]:
    """Paragraph-group chunking for heading-less documents.

    Consecutive paragraphs are merged up to FLAT_TARGET_CHARS, then each
    resulting group is labelled by classifying its own content — so a fever
    page yields separate retrievable 'causes' and 'treatment' chunks even
    though the source has no headings at all.
    """
    body_blocks = [(kind, text) for kind, text in blocks if kind in ("p", "list")]
    if not body_blocks:
        return []

    groups: list[str] = []
    current: list[str] = []
    current_len = 0
    for kind, text in body_blocks:
        # Start a new group when adding this block would overshoot the
        # target — but only at a legitimate boundary (never orphaning a
        # list from its lead-in sentence).
        if (
            current
            and current_len + len(text) > FLAT_TARGET_CHARS
            and _can_break_before(current[-1], kind)
        ):
            groups.append(" ".join(current))
            current, current_len = [], 0
        current.append(text)
        current_len += len(text)
    if current:
        groups.append(" ".join(current))

    chunks: list[RawChunk] = []
    for group in groups:
        if len(group) < MIN_CHUNK_CHARS:
            # Too small to stand alone — append to the previous chunk.
            if chunks:
                chunks[-1].text = f"{chunks[-1].text} {group}".strip()
            continue
        category = classify_section("", group)
        chunks.append(RawChunk(heading=_derive_heading(category), text=group, category=category))
    return chunks


def _derive_heading(category: str) -> str:
    from app.rag.sections import category_label

    return category_label(category)


def chunk_drug_info_page(html: str) -> list[RawChunk]:
    """Chunk a real MedlinePlus drug-info page into its labelled sections
    (uses, precautions, side effects, overdose, etc.)."""
    soup = BeautifulSoup(html, "lxml")
    chunks: list[RawChunk] = []
    for section in soup.select("div.section"):
        heading_el = section.select_one(".section-title") or section.find(["h2", "h3"])
        body_el = section.select_one(".section-body")
        heading = _clean_text(heading_el.get_text(" ")) if heading_el else "Section"
        body = _clean_text(body_el.get_text(" ")) if body_el else _clean_text(section.get_text(" "))
        if len(body) >= MIN_CHUNK_CHARS:
            chunks.append(
                RawChunk(heading=heading, text=body, category=classify_section(heading, body, "drug_info"))
            )
    return [c for chunk in chunks for c in _split_chunk_if_long(chunk)]


def _split_long(text: str, size: int = MAX_CHUNK_CHARS) -> list[str]:
    words = text.split(" ")
    out: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + 1 > size and cur:
            out.append(" ".join(cur))
            cur, cur_len = [], 0
        cur.append(w)
        cur_len += len(w) + 1
    if cur:
        out.append(" ".join(cur))
    return out


def _split_chunk_if_long(chunk: RawChunk) -> list[RawChunk]:
    if len(chunk.text) <= MAX_CHUNK_CHARS:
        return [chunk]
    return [
        RawChunk(heading=chunk.heading, text=part, category=chunk.category)
        for part in _split_long(chunk.text)
    ]
