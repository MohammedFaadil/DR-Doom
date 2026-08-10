# 🩺 DR DOOM

**Evidence-grounded health intelligence.**

An AI-assisted clinical *information and triage* companion — structured
symptom intake, hybrid RAG over a real curated medical knowledge base,
deterministic emergency detection, grounded/cited answers, and a premium
React chat UI with voice I/O. No commercial LLM API key required.

> Dr Doom provides AI-generated health information and educational guidance
> based on its available medical knowledge sources. It is not a substitute
> for an examination, diagnosis, or treatment from a qualified healthcare
> professional. If symptoms are severe, sudden, or concerning, seek
> appropriate medical care.

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Why RAG, not "just prompt an LLM"](#3-why-rag-not-just-prompt-an-llm)
4. [Model architecture](#4-model-architecture)
5. [Knowledge base](#5-knowledge-base)
6. [Safety architecture](#6-safety-architecture)
7. [Database](#7-database)
8. [Voice system](#8-voice-system)
9. [Frontend](#9-frontend)
10. [Backend](#10-backend)
11. [Local development](#11-local-development)
12. [Environment variables](#12-environment-variables)
13. [Knowledge ingestion](#13-knowledge-ingestion)
14. [Testing & evaluation](#14-testing--evaluation)
15. [Render deployment](#15-render-deployment)
16. [Performance & Render Free optimization](#16-performance--render-free-optimization)
17. [Security](#17-security)
18. [Privacy](#18-privacy)
19. [Limitations — what's deliberately simplified](#19-limitations--whats-deliberately-simplified)
20. [Medical safety disclaimer](#20-medical-safety-disclaimer)

---

## 1. Project overview

Dr Doom is built to feel like *"an evidence-grounded clinical information and
triage assistant"* — not a chatbot pretending to be a doctor. Its
intelligence comes from structured clinical questioning + real retrieval +
deterministic safety rules + grounding validation, not from a single giant
LLM prompt.

What it does:
- Understands a free-text complaint, then asks **one clinically relevant
  question at a time** (clickable options where sensible, free text where
  not), stopping as soon as it has enough information.
- Screens **every turn** for emergency red flags with a deterministic rule
  engine — before any generation happens.
- Retrieves real evidence (hybrid semantic + keyword search) from a
  knowledge base built live from **MedlinePlus (U.S. National Library of
  Medicine / NIH)** — never hand-written or scraped-blog content.
- Composes an answer strictly from that evidence, then re-validates every
  sentence against the retrieved chunks (grounding validator) before
  showing it, stripping anything unsupported.
- Shows real, clickable citations for every factual claim.
- Persists conversations, generates a structured consultation summary, and
  exports it as a PDF.
- Supports voice input/output natively in the browser.

## 2. Architecture

```
USER QUERY
  -> Conversation Context (patient_state, persisted per conversation)
  -> Intake Agent            (symptom/entity extraction, intent detection)
  -> EmergencyRiskEngine     (deterministic red-flag rules — ALWAYS first)
  -> Question Agent          (adaptive next-question selection, or "done")
  -> Retrieval Agent         (query rewriting + hybrid search)
  -> Hybrid Retriever        (FAISS semantic + BM25 keyword, reranked)
  -> Clinical Explanation Agent (composes response from evidence + state)
  -> ModelManager            (template / local_transformers / ollama)
  -> GroundingValidator      (strips any unsupported sentence)
  -> Medication Safety Agent (medication questions only; KB-only answers)
  -> Summary Agent           (consultation summary, on completion)
  -> Response Formatter (FastAPI) -> React UI
```

Each stage above is a separate, independently-testable Python module under
`backend/app/agents/` and `backend/app/safety/` — not one giant prompt. See
`backend/app/agents/orchestrator.py` for the deterministic state machine
that sequences them (`WELCOME → COMPLAINT_COLLECTION → RED_FLAG_SCREENING →
FOLLOW_UP → EVIDENCE_RETRIEVAL → ASSESSMENT → GUIDANCE → SUMMARY →
COMPLETE`, with an `ANY_STATE → EMERGENCY` branch).

## 3. Why RAG, not "just prompt an LLM"

An LLM asked "what could cause X" will confidently produce plausible-sounding
but sometimes wrong medical claims, fake citations, or fabricated drug
information — unacceptable for health content (§90 "no hallucination rule").
Instead:

- All factual claims must trace back to a **retrieved** MedlinePlus chunk.
- The **default** response composer (`MODEL_PROVIDER=template`) doesn't call
  a generative model at all — it deterministically assembles the response
  from the retrieved text itself, so there is structurally no way for it to
  invent a fact.
- If a heavier `local_transformers`/`ollama` provider is enabled to
  paraphrase the composed text more conversationally, the
  **GroundingValidator** re-checks every sentence of its output against the
  retrieved evidence by embedding similarity *and* a deterministic
  named-entity/year check, stripping anything that doesn't match — so even
  a hallucination-prone provider can't get a fabricated name, date, or claim
  through.
- If retrieval doesn't find anything relevant, the app says so explicitly
  ("I don't have enough evidence in my verified medical knowledge base to
  answer that safely") instead of answering from general model knowledge.

## 4. Model architecture

`backend/app/core/model_registry.py` defines a small provider interface
(`GenerationProvider.rephrase(composed_text) -> text`) with three
implementations, selected via `MODEL_PROVIDER`:

| Provider | What it does | RAM | Default |
|---|---|---|---|
| `template` | Deterministic pass-through — the actual "model" is the structured template composer in `app/agents/explanation.py`. Zero extra RAM. | ~0 | ✅ yes |
| `local_transformers` | Loads a small local HF instruct model (e.g. `Qwen/Qwen2.5-0.5B-Instruct`) to paraphrase the composed text in plainer language. Lazy-loaded on first use. | ~1-2 GB | no |
| `ollama` | Calls a locally-running Ollama server over HTTP. | depends on your Ollama setup | no |

`ModelManager` (`app/core/model_manager.py`) wraps whichever provider is
configured and **always falls back to `template`** if the configured
provider fails to load or errors at call time (§47) — the app never
crashes or silently returns nothing just because a model failed.

**Why `template` is the default:** Render Free gives ~512MB RAM shared with
the rest of the app (DB connections, FAISS index, embedding model). A real
LLM — even a small quantized one — does not reliably fit alongside that,
and pretending otherwise (§92 "do not fake functionality") would mean
either crashing on deploy or silently returning nothing. The deterministic
template composer is not a placeholder — it's the intentional, permanently
correct default for a resource-constrained deployment, and it's what keeps
grounding trivially perfect (the text *is* the evidence). Swapping to
`local_transformers` or `ollama` needs zero application code changes,
only environment variables + (for `local_transformers`)
`pip install -r requirements-full.txt`.

## 5. Knowledge base

**Not** scraped blogs, **not** hand-written by an LLM. `scripts/ingest_documents.py`
pulls real content live from two public NIH/NLM APIs:

- **MedlinePlus Web Service** (`wsearch.nlm.nih.gov`) — consumer
  health-topic summaries, for ~55 curated topics spanning general medicine,
  cardiovascular, respiratory, GI, dermatology, mental wellbeing, women's/
  men's health, pediatrics, and elderly care (`backend/app/knowledge_config.py`
  lists the topic manifest — itself just a list of search *queries* and our
  own clinical tags, containing no medical claims).
- **RxNorm + MedlinePlus Connect** — resolves a drug name to a real RxCUI,
  then to a real MedlinePlus consumer drug-information page, for ~20 common
  OTC/Rx medications.

Each ingested chunk carries real source metadata (title, organization, URL,
document type, medical domain, ingestion date) — see `app/rag/types.py`. If
a topic/drug lookup fails, it's skipped and logged, **never** replaced with
fabricated content.

Pipeline: fetch → clean (`app/rag/chunking.py`, heading-aware — preserves
section structure like "precautions"/"side effects" rather than blind
500-char splitting) → attach metadata → embed
(`BAAI/bge-small-en-v1.5` via `fastembed`, ONNX/CPU, no torch) → build a
FAISS `IndexFlatIP` (cosine similarity) + a `rank_bm25` keyword index →
persist to `backend/knowledge_base/index/`.

Retrieval (`app/rag/hybrid.py`) combines both scores
(`0.70·semantic + 0.30·keyword`, configurable) with metadata filtering, then
reranks with a deterministic authority/heading-match booster
(`app/rag/rerank.py`) — every source in this build is MedlinePlus/NIH, so
the authority weighting is mostly future-proofing for adding more sources
later.

## 6. Safety architecture

- **`EmergencyRiskEngine`** (`app/safety/emergency_engine.py`) — plain
  Python regex + structured-state rules for severe breathing difficulty,
  loss of consciousness, stroke signs, severe chest pain, uncontrolled
  bleeding, anaphylaxis, seizures, suicidal crisis, poisoning, testicular
  torsion, pediatric infant fever, febrile seizure. Runs on **every** turn,
  **before** intake/retrieval/generation — deterministic, not model-judged.
- **`GroundingValidator`** (`app/safety/grounding_validator.py`) — sentence-
  level claim checking against retrieved evidence (embedding similarity +
  a proper-noun/year entailment check), strips unsupported sentences.
- **`MedicationSafetyEngine`** (`app/safety/medication_safety.py`) — answers
  only from ingested drug chunks; flags allergy conflicts, pregnancy,
  pediatric, and elderly considerations from the patient's profile; refuses
  outright for any drug not in the knowledge base.
- **Prompt/document injection defense** — retrieved chunks and user text are
  always treated as *data*, never as instructions. The default `template`
  provider never sends retrieved text to a model as an instruction-following
  prompt at all (it just string-formats it); the `local_transformers`
  provider's prompt is a fixed rewrite-only instruction, and grounding
  validation runs on its output regardless.

## 7. Database

SQLAlchemy models (`backend/app/models/`): `users`, `health_profiles`,
`conversations`, `messages`, `conversation_summaries`, `clinical_assessments`,
`retrieval_logs`, `citations`, `feedback`, `consent_records`. PostgreSQL in
production via `DATABASE_URL`; SQLite fallback for local dev/tests only —
**see the storage-constraint note below**. Tables are created via
`Base.metadata.create_all()` at startup rather than Alembic migrations
(a deliberate scope trade-off for this build — see §19).

### Render Free storage constraint

Render Free web-service filesystems are **ephemeral** — anything written to
local disk (SQLite, uploaded files) disappears on redeploy/restart. This app
never relies on that for anything that must persist: all application data
lives in PostgreSQL. The prebuilt knowledge base index is committed to the
repo and baked into the Docker image (not written at runtime), so it
survives redeploys too. Render's **Free Postgres** plan itself is
time/size-limited — this is a demo/prototype deployment target, not a
promise of permanent medical-record storage.

## 8. Voice system

Entirely browser-native, zero backend cost, built directly into the chat
composer (`frontend/src/hooks/useVoice.ts`):

- **STT:** the Web Speech API (`SpeechRecognition`/`webkitSpeechRecognition`)
  — tap the mic, speak, see live transcription in the composer, edit before
  sending.
- **TTS:** `speechSynthesis` — a "Listen" button on every assistant message.
- Both gracefully degrade: `sttSupported`/`ttsSupported` flags hide the
  controls entirely in unsupported browsers, falling back to typing.

`POST /api/voice/transcribe` exists as a documented server-side interface
(for a future `faster-whisper` integration) but returns a clear `501` by
default (`ENABLE_SERVER_TRANSCRIBE=false`) — Render Free cannot host a
Whisper model reliably alongside everything else, so this build doesn't
pretend to (§92).

## 9. Frontend

React 18 + TypeScript + Vite + Tailwind CSS. `frontend/src/`:
`components/` (chat: message bubbles, typed question renderer, emergency
banner, live assessment panel, voice controls; `common/`: buttons, cards,
risk badges), `pages/` (Landing, Login, Register, Dashboard, Chat, History,
Profile, Settings, Admin), `layouts/` (`AppLayout` — sidebar on desktop,
bottom nav on mobile), `stores/` (Zustand: auth, theme), `hooks/`
(`useVoice`), `services/` (typed `fetch` wrappers per resource).

Design system: brand teal (`brand-*`) + neutral ink scale, light/dark via
Tailwind's `class` strategy (`stores/themeStore.ts`), rounded cards,
`prose-dr` markdown styling for assistant messages (`react-markdown` +
`remark-gfm`), skeleton/loading-dots states, mobile-first with a bottom nav.

## 10. Backend

FastAPI (`backend/app/`): `api/` (routers), `agents/` (the pipeline stages
above), `rag/` (embeddings, vector/keyword stores, hybrid retrieval,
chunking, normalization, reranking), `core/` (model registry/manager),
`clinical/` (state machine building blocks, question bank, symptom
lexicon), `safety/` (emergency engine, grounding validator, medication
safety), `models/` + `schemas/` (SQLAlchemy + Pydantic), `services/` (PDF
export), `auth/` (JWT + bcrypt), `voice/`.

## 11. Local development

**Backend:**
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
cp ../.env.example .env       # edit if needed — SQLite fallback works out of the box
python scripts/ingest_documents.py   # builds the real knowledge base index (~2-3 min)
uvicorn app.main:app --reload
```
Backend runs at `http://127.0.0.1:8000` (or whatever `--port` you choose).

**Frontend:**
```bash
cd frontend
npm install
cp ../.env.frontend.example .env   # leave VITE_API_URL empty, set VITE_PROXY_TARGET to your backend
npm run dev
```
Frontend runs at `http://localhost:5173` and proxies `/api/*` to your
backend (see `vite.config.ts`) — this keeps frontend+backend same-origin in
dev so the session cookie works as plain `SameSite=Lax` without any CORS
juggling. In production the two are genuinely cross-origin — see
[§17 Security](#17-security) and `.env.example` for `COOKIE_SAMESITE=none`.

## 12. Environment variables

See [`.env.example`](.env.example) (backend) and
[`.env.frontend.example`](.env.frontend.example) (frontend) — every
variable is documented inline.

## 13. Knowledge ingestion

```bash
cd backend
python scripts/ingest_documents.py             # full run (~55 topics + ~20 drugs)
python scripts/ingest_documents.py --limit 3    # quick smoke test
```
Outputs: `knowledge_base/raw/` (fetched HTML, gitignored), `chunks/all_chunks.jsonl`,
`metadata/manifest.json`, `index/{vectors.faiss,chunks.json,bm25.pkl,bm25_chunks.json}`.
Re-run any time to refresh content or add topics/drugs to
`app/knowledge_config.py`; bump `KNOWLEDGE_VERSION` in `.env` after a
meaningful refresh (§89 — every response is traceable to a knowledge
version via `Conversation.knowledge_version`).

## 14. Testing & evaluation

```bash
cd backend
pytest tests/ -q                    # 37 tests: emergency engine, grounding,
                                     # question engine, symptom lexicon,
                                     # auth API, chat API, medication safety,
                                     # retrieval (skipped if index not built)
python evaluation/evaluate.py       # 12-scenario safety benchmark
```

The evaluation harness measures Emergency Recall, response-type accuracy,
and a grounded-answer-rate proxy against a small **synthetic** scenario
suite (`evaluation/scenarios.json`) — this is a regression check on the
deterministic safety layer, **not a clinical validation claim**. Numbers
are printed as measured, never rounded up to "100% accurate" (§62, §90).

## 15. Render deployment

See [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md) for the full step-by-step guide,
or use [`render.yaml`](render.yaml) as a one-click Blueprint.

## 16. Performance & Render Free optimization

- Embedding model + vector/keyword index are loaded once at startup
  (`app/rag/index_manager.py`, `lru_cache`) and reused for every request —
  never rebuilt or reloaded per-request.
- `MODEL_PROVIDER=template` means zero LLM inference cost by default.
- `GET /api/health` responds immediately without waiting on the full
  startup sequence; `GET /api/readiness` separately reports DB/index/model
  status so the app never silently answers with an unready knowledge base.
- `POST /api/chat/stream` (SSE) streams status updates
  ("Retrieving evidence…" → "Assessing…" → "Preparing response…" → final
  answer) so the UI feels responsive even though inference is CPU-only.
- Retrieval is capped at `RETRIEVAL_TOP_K` (default 6); conversation context
  sent to any generative provider is the current patient_state + retrieved
  evidence, never the full raw message history.
- The knowledge base index ships prebuilt in the Docker image — the
  container never downloads/builds it at boot.

## 17. Security

CORS allowlist (`CORS_ORIGINS`), per-route rate limiting (`slowapi` —
stricter limits on `/api/auth/*` and `/api/voice/*` than `/api/chat`),
Pydantic input validation on every endpoint, bcrypt password hashing,
HTTP-only JWT session cookies with configurable `Secure`/`SameSite`,
security response headers (`X-Frame-Options`, `X-Content-Type-Options`,
`Content-Security-Policy`, `Referrer-Policy`), non-root Docker user,
secrets via environment variables only (never committed), generic error
responses (no stack traces leaked — see `app/main.py` exception handlers).
`grep -ri "OPENAI_API_KEY\|ANTHROPIC_API_KEY\|GEMINI_API_KEY\|GROQ_API_KEY"`
across the repo returns nothing — no commercial LLM API key is required or
referenced anywhere in the default path.

## 18. Privacy

No request/response body logging middleware is installed —
`app/utils/logging_config.py` documents this explicitly; application code
never logs full patient_state or message content, only identifiers and
latencies. Users can delete a single conversation, delete their entire
health profile, export their data as JSON, or delete their account outright
(cascades to all owned data via ORM relationships) — see Settings and
Profile pages / `DELETE /api/auth/me`, `/api/profile`,
`/api/conversations/{id}`.

## 19. Limitations — what's deliberately simplified

Stated plainly rather than silently faked (§92, §99):

- **No bundled large medical LLM.** `template` mode (deterministic,
  evidence-composed) is the default and the only mode guaranteed to work on
  Render Free. `local_transformers`/`ollama` are real, wired-up, working
  providers behind the same interface — just not the default, because Free
  tier RAM can't reliably host them.
- **No server-side speech-to-text model.** Browser Web Speech API is the
  real default; a server endpoint interface exists for a future
  `faster-whisper` upgrade but is off by default.
- **No bundled Ollama/llama.cpp binary.** The `ollama` provider genuinely
  works if you have Ollama running somewhere reachable — it's just not part
  of the default zero-config deploy.
- **Hindi/Tamil are scaffolded, not shipped.** The health profile has a
  `preferred_language` field, the frontend has a language selector, but the
  clinical knowledge base and generation pipeline are English-only today —
  the Settings page says so explicitly rather than silently mistranslating
  medical guidance.
- **No Alembic migrations** — `create_all()` at startup. Fine for a fresh
  deploy/demo; introduce Alembic before a first production schema change.
- **Single-turn evaluation harness.** `evaluation/evaluate.py` scores each
  scenario as a single turn (not a full multi-turn conversation replay),
  so "grounded answer rate" undercounts scenarios that correctly stop at a
  follow-up question rather than a final answer — see the script's own
  comments.

## 20. Medical safety disclaimer

Dr Doom provides AI-generated health information and educational guidance
based on its available medical knowledge sources. It is not a substitute
for an examination, diagnosis, or treatment from a qualified healthcare
professional. It does not claim 100% accuracy, does not claim to be a
licensed physician, and does not issue prescriptions. If symptoms are
severe, sudden, or concerning, seek appropriate medical care — in an
emergency, call your local emergency number immediately.
#   D R - D o o m  
 