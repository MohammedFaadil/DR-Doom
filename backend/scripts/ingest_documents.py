"""
Knowledge ingestion pipeline (§8).

DOCUMENT -> extract text -> clean -> chunk (heading-aware) -> attach
metadata -> embed -> build vector + keyword index -> persist.

Fetches REAL content live from two U.S. National Library of Medicine (NIH)
public APIs — nothing here is scraped from arbitrary blogs and nothing is
hand-authored by an LLM:

  * MedlinePlus Web Service (wsearch) — consumer health-topic summaries
    https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term=...
  * RxNorm + MedlinePlus Connect — resolves a drug name to a real RxCUI,
    then to a real MedlinePlus consumer drug-information page
    https://rxnav.nlm.nih.gov/REST/rxcui.json?name=...
    https://connect.medlineplus.gov/service?...

If a lookup or fetch fails for a given topic/drug, it is skipped and logged
— never replaced with fabricated content (§90).

Usage:
    python scripts/ingest_documents.py [--limit N] [--skip-drugs] [--skip-topics]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.rag.chunking import chunk_drug_info_page, chunk_health_topic_summary  # noqa: E402
from app.rag.embeddings import get_embedding_model  # noqa: E402
from app.rag.keyword_store import KeywordStore  # noqa: E402
from app.rag.types import DocumentChunk  # noqa: E402
from app.rag.vector_store import VectorStore  # noqa: E402
from app.knowledge_config import DRUGS, TOPICS, DrugSource, TopicSource  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingest")

WSEARCH_URL = "https://wsearch.nlm.nih.gov/ws/query"
RXNORM_URL = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
CONNECT_URL = "https://connect.medlineplus.gov/service"
USER_AGENT = "DrDoomIngest/1.0 (educational healthcare RAG demo)"

BACKEND_ROOT = Path(__file__).resolve().parent.parent
KB_ROOT = BACKEND_ROOT / "knowledge_base"
TODAY = date.today().isoformat()


def _http_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20.0, follow_redirects=True)


# ---------------------------------------------------------------------------
# Health topics (MedlinePlus wsearch)
# ---------------------------------------------------------------------------

def fetch_health_topic(client: httpx.Client, source: TopicSource) -> DocumentChunk | list[DocumentChunk] | None:
    resp = client.get(WSEARCH_URL, params={"db": "healthTopics", "term": source.query, "retmax": 5})
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    documents = root.findall(".//document")
    if not documents:
        logger.warning("[topic:%s] no MedlinePlus results for %r", source.slug, source.query)
        return None

    best = documents[0]
    title_raw = _content_text(best, "title")
    title = BeautifulSoup(title_raw, "lxml").get_text(" ").strip()
    organization = _content_text(best, "organizationName") or "National Library of Medicine"
    url = best.get("url", "")
    full_summary_html = _content_text(best, "FullSummary")

    if not full_summary_html or not url:
        logger.warning("[topic:%s] missing summary/url, skipping", source.slug)
        return None

    raw_chunks = chunk_health_topic_summary(full_summary_html)
    if not raw_chunks:
        logger.warning("[topic:%s] produced 0 chunks, skipping", source.slug)
        return None

    doc_id = f"topic:{source.slug}"
    out: list[DocumentChunk] = []
    for i, rc in enumerate(raw_chunks):
        out.append(
            DocumentChunk(
                chunk_id=f"{doc_id}#{i}",
                doc_id=doc_id,
                title=title,
                organization=organization,
                url=url,
                source_type="health_topic",
                medical_domain=source.medical_domain,
                section_heading=rc.heading,
                section_category=rc.category,
                text=rc.text,
                tags=list(source.tags),
                document_type="consumer health summary",
                country="US",
                version="1",
                last_reviewed=TODAY,
                publication_date=None,
            )
        )

    _save_raw(f"topic_{source.slug}", full_summary_html)
    return out


def _content_text(document_el: ET.Element, name: str) -> str:
    el = document_el.find(f".//content[@name='{name}']")
    return (el.text or "") if el is not None else ""


# ---------------------------------------------------------------------------
# Drug information (RxNorm -> MedlinePlus Connect -> real druginfo page)
# ---------------------------------------------------------------------------

def _resolve_rxcui(client: httpx.Client, name: str) -> str | None:
    # Exact match first (tends to return the ingredient-level concept).
    for params in ({"name": name}, {"name": name, "search": 1}):
        resp = client.get(RXNORM_URL, params=params)
        if resp.status_code != 200:
            continue
        data = resp.json()
        rxcui_list = data.get("idGroup", {}).get("rxnormId")
        if rxcui_list:
            return rxcui_list[0]
    return None


def _resolve_druginfo_url(client: httpx.Client, rxcui: str) -> tuple[str, str] | None:
    resp = client.get(
        CONNECT_URL,
        params={
            "mainSearchCriteria.v.c": rxcui,
            "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.88",
            "informationRecipient.languageCode.c": "en",
            "knowledgeResponseType": "application/json",
        },
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    entries = data.get("feed", {}).get("entry")
    if not entries:
        return None
    entry = entries[0] if isinstance(entries, list) else entries
    links = entry.get("link", [])
    if isinstance(links, dict):
        links = [links]
    if not links:
        return None
    href = links[0]["href"].split("?")[0]
    title = entry.get("title", {}).get("_value", "")
    if "medlineplus.gov/druginfo" not in href:
        return None
    return href, title


def fetch_drug(client: httpx.Client, source: DrugSource) -> list[DocumentChunk] | None:
    rxcui = _resolve_rxcui(client, source.name)
    if not rxcui:
        logger.warning("[drug:%s] could not resolve RxCUI, skipping", source.slug)
        return None
    resolved = _resolve_druginfo_url(client, rxcui)
    if not resolved:
        logger.warning("[drug:%s] MedlinePlus Connect returned no drug-info page, skipping", source.slug)
        return None
    url, title = resolved

    resp = client.get(url)
    if resp.status_code != 200:
        logger.warning("[drug:%s] failed to fetch %s (%s), skipping", source.slug, url, resp.status_code)
        return None

    raw_chunks = chunk_drug_info_page(resp.text)
    if not raw_chunks:
        logger.warning("[drug:%s] produced 0 chunks, skipping", source.slug)
        return None

    doc_id = f"drug:{source.slug}"
    out: list[DocumentChunk] = []
    for i, rc in enumerate(raw_chunks):
        out.append(
            DocumentChunk(
                chunk_id=f"{doc_id}#{i}",
                doc_id=doc_id,
                title=title or source.name.title(),
                organization="National Library of Medicine",
                url=url,
                source_type="drug_info",
                medical_domain="medication",
                section_heading=rc.heading,
                section_category=rc.category,
                text=rc.text,
                tags=[source.drug_class],
                document_type="consumer medication information",
                country="US",
                version="1",
                last_reviewed=TODAY,
                publication_date=None,
            )
        )
    _save_raw(f"drug_{source.slug}", resp.text)
    return out


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _save_raw(name: str, content: str) -> None:
    (KB_ROOT / "raw").mkdir(parents=True, exist_ok=True)
    (KB_ROOT / "raw" / f"{name}.html").write_text(content, encoding="utf-8")


def _save_chunks(all_chunks: list[DocumentChunk]) -> None:
    chunks_dir = KB_ROOT / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    with open(chunks_dir / "all_chunks.jsonl", "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")

    meta_dir = KB_ROOT / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    doc_ids = sorted({c.doc_id for c in all_chunks})
    (meta_dir / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "document_count": len(doc_ids),
                "chunk_count": len(all_chunks),
                "document_ids": doc_ids,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def build_index(all_chunks: list[DocumentChunk]) -> None:
    settings = get_settings()
    model = get_embedding_model()
    logger.info("Embedding %d chunks with %s ...", len(all_chunks), settings.EMBEDDING_MODEL)
    texts = [f"{c.title} — {c.section_heading}: {c.text}" for c in all_chunks]
    vectors = model.embed(texts)

    vector_store = VectorStore(dimension=model.dimension)
    vector_store.add(vectors, all_chunks)
    vector_store.save(settings.VECTOR_INDEX_PATH)

    keyword_store = KeywordStore()
    keyword_store.build(all_chunks)
    keyword_store.save(settings.VECTOR_INDEX_PATH)

    logger.info("Index built at %s (%d chunks)", settings.VECTOR_INDEX_PATH, len(all_chunks))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="limit number of topics/drugs (debug)")
    parser.add_argument("--skip-drugs", action="store_true")
    parser.add_argument("--skip-topics", action="store_true")
    args = parser.parse_args()

    all_chunks: list[DocumentChunk] = []
    skipped: list[str] = []

    with _http_client() as client:
        if not args.skip_topics:
            topics = TOPICS[: args.limit] if args.limit else TOPICS
            for i, topic in enumerate(topics):
                logger.info("(%d/%d) topic: %s", i + 1, len(topics), topic.slug)
                try:
                    chunks = fetch_health_topic(client, topic)
                except Exception:  # noqa: BLE001
                    logger.exception("[topic:%s] failed", topic.slug)
                    chunks = None
                if chunks:
                    all_chunks.extend(chunks)
                else:
                    skipped.append(f"topic:{topic.slug}")
                time.sleep(0.15)  # be a polite API citizen

        if not args.skip_drugs:
            drugs = DRUGS[: args.limit] if args.limit else DRUGS
            for i, drug in enumerate(drugs):
                logger.info("(%d/%d) drug: %s", i + 1, len(drugs), drug.slug)
                try:
                    chunks = fetch_drug(client, drug)
                except Exception:  # noqa: BLE001
                    logger.exception("[drug:%s] failed", drug.slug)
                    chunks = None
                if chunks:
                    all_chunks.extend(chunks)
                else:
                    skipped.append(f"drug:{drug.slug}")
                time.sleep(0.15)

    if not all_chunks:
        logger.error("No chunks ingested — aborting index build.")
        sys.exit(1)

    _save_chunks(all_chunks)
    build_index(all_chunks)

    logger.info("=" * 60)
    logger.info("Ingestion complete: %d chunks from %d documents", len(all_chunks), len({c.doc_id for c in all_chunks}))
    if skipped:
        logger.warning("Skipped %d sources (no fabricated substitute used): %s", len(skipped), ", ".join(skipped))


if __name__ == "__main__":
    main()
