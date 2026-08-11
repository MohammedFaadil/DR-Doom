# 🩺 DR DOOM

**Evidence-grounded health intelligence.**

An AI-assisted clinical *information and triage* companion — structured
symptom intake, hybrid RAG over a real curated medical knowledge base,
deterministic emergency detection, grounded/cited answers, real-time
streaming responses with full conversation memory, and a premium React
chat UI with voice I/O. Powered by **Groq** (Llama 3.3 70B) for genuinely
intelligent, context-aware answers — with a zero-dependency deterministic
fallback so the app never breaks if that's unavailable.

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
- Composes an answer directly from that evidence **and the conversation so
  far** (so a follow-up like "is it OK to take ibuprofen for it?" correctly
  reasons about the headache you mentioned three turns ago), then
  re-validates every sentence against the retrieved chunks (grounding
  validator) before showing it, stripping anything unsupported.
- Streams the validated answer to the UI progressively (real-time feel),
  and shows a live grounding-confidence indicator plus real, clickable
  citations for every factual claim.
- Persists conversations, generates a structured consultation summary, and
  exports it as a PDF.
- Supports voice input/output natively in the browser.

## 2. Architecture

```
USER QUERY
  -> Conversation Context (patient_state + recent message history, persisted per conversation)
  -> Intake Agent            (symptom/entity extraction, intent detection)
  -> EmergencyRiskEngine     (deterministic red-flag rules — ALWAYS first)
  -> Question Agent          (adaptive next-question selection, or "done")
  -> Retrieval Agent         (query rewriting + hybrid search)
  -> Hybrid Retriever        (FAISS semantic + BM25 keyword, reranked)
  -> Clinical Explanation Agent (evidence + history -> grounded-RAG prompt)
  -> ModelManager            (groq / template / llama_cpp / local_transformers / ollama)
  -> GroundingValidator      (strips any unsupported sentence, catches dropped sections)
  -> Medication Safety Agent (medication questions only; KB-only answers, never LLM-touched)
  -> Summary Agent           (consultation summary, on completion)
  -> SSE Stream (FastAPI) -> React UI (progressive reveal + confidence UI)
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
So even though the production default (`MODEL_PROVIDER=groq`) is a real,
capable 70B model, it is never given free rein to just answer from its own
training knowledge:

- All factual claims must trace back to a **retrieved** MedlinePlus chunk.
  Groq is handed that retrieved evidence *as the only source of medical
  facts* in its system prompt, explicitly instructed to say "I don't have
  enough evidence" rather than fill a gap from general knowledge, and told
  never to name a specific serious condition (stroke, cancer, etc.) unless
  it's literally present in the evidence — see
  `app/agents/explanation.py::_GROQ_SYSTEM_PROMPT_TEMPLATE`.
- **GroundingValidator** re-checks every sentence of the model's output
  afterward regardless — by embedding similarity against the retrieved
  chunks, a deterministic named-entity/year check, *and* a check for
  specific high-stakes clinical terms (stroke, tumor, heart attack, ...)
  that must already be present in the evidence to survive. This is defense
  in depth: the strict prompt lowers how often a claim needs to be caught,
  the validator is what actually guarantees it never reaches the user
  unchecked.
- If the model's answer drops whole sections or shrinks drastically
  relative to what the deterministic composer would have produced (a real,
  observed small-model failure mode — see §4), the app discards it and
  falls back to the deterministic version rather than showing an
  incomplete answer.
- The **fallback** response composer (`MODEL_PROVIDER=template`, and what
  `groq` itself falls back to on any failure) doesn't call a generative
  model at all — it deterministically assembles the response from the
  retrieved text itself, so there is structurally no way for it to invent
  a fact. This is what keeps the app fully functional even with no API key
  configured at all.
- If retrieval doesn't find anything relevant, the app says so explicitly
  ("I don't have enough evidence in my verified medical knowledge base to
  answer that safely") instead of answering from general model knowledge.

## 4. Model architecture

`backend/app/core/model_registry.py` defines a provider interface with
five implementations, selected via `MODEL_PROVIDER`:

| Provider | What it does | RAM (measured) | Default |
|---|---|---|---|
| `groq` | Groq-hosted **Llama 3.3 70B Versatile** via their OpenAI-compatible Chat Completions API (LPU inference — fast even at 70B). Composes the answer directly from retrieved evidence + conversation history, not just a rephrase. Needs `GROQ_API_KEY`. | 0 (runs on Groq's infra) | ✅ yes |
| `template` | Deterministic pass-through — the actual "model" is the structured template composer in `app/agents/explanation.py`. Zero extra RAM. The automatic fallback if Groq is unavailable. | ~0 | fallback |
| `llama_cpp` | Quantized GGUF model (`SmolLM2-360M-Instruct`) via `llama-cpp-python` — pure C++ inference, no torch. For **local testing without an API key**. | ~350-450MB extra | opt-in |
| `local_transformers` | Loads a small local HF instruct model (e.g. `Qwen/Qwen2.5-0.5B-Instruct`) via `transformers`/torch. Heavier, for local dev on a machine with real RAM. | ~2GB+ extra | opt-in |
| `ollama` | Calls a locally-running Ollama server over HTTP. | depends on your Ollama setup | opt-in |

`ModelManager` (`app/core/model_manager.py`) wraps whichever provider is
configured and **always falls back to `template`** if the configured
provider is unavailable (e.g. no API key), fails, errors at call time, or
produces an answer that drops whole sections or shrinks drastically
relative to the deterministic version (§47, and see
`app/agents/explanation.py::_generate_grounded` /
`_rephrase_or_fallback`) — the app never crashes, hangs, or silently
returns an incomplete answer just because the model under-delivered.

### Why Groq, and how it actually reasons over evidence + history

Most "add an LLM" implementations just ask a model to paraphrase
already-composed text. Groq mode goes further:
`explanation.py::_generate_grounded` hands the model the **raw retrieved
evidence chunks** (not a pre-filtered template) plus the **recent
conversation history** as real chat turns, inside a strict system prompt
(`_GROQ_SYSTEM_PROMPT_TEMPLATE`) that says: answer only from this evidence,
never invent a specific serious condition unless it's literally present,
use history for context/consistency only — never as a source of new
medical facts. This is what makes a follow-up question like *"is it OK to
take ibuprofen for this?"* correctly connect back to the headache
discussed three turns earlier and the pregnancy status mentioned during
intake, rather than being answered in a vacuum. `GroundingValidator` still
re-checks the output afterward exactly like every other provider (§3) —
capability lowers how often the safety net has to catch something, it
doesn't replace it.

Conversation history is windowed to the most recent
`CONVERSATION_HISTORY_TURNS` turns (default 8) by `app/api/chat.py`, so
prompt size/cost/latency stays bounded regardless of how long a
conversation gets — Groq's actual context window (128K tokens) is far
larger than this app ever needs.

### Why `template` is the safety-net default, not `groq` blindly

The app is deliberately built so that **no API key at all still works,
fully, forever** — `MODEL_PROVIDER` defaults to `template` in
`app/config.py`, and every deploy path (`render.yaml`, `.env.example`)
requires an explicit, conscious choice to turn Groq on. If `GROQ_API_KEY`
is empty, `GroqProvider.is_available()` returns `False` and `ModelManager`
transparently uses `template` instead — same deterministic,
evidence-composed answers as always, just without the natural-language
polish and cross-turn reasoning Groq adds.

### Local testing without an API key: one-line model swap

Don't have a Groq key handy, or want to test fully offline? Change one
value in `backend/.env`:

```bash
# .env
MODEL_PROVIDER=llama_cpp   # was: groq
```

That's it — no code changes. `llama_cpp` uses a quantized
`SmolLM2-360M-Instruct` GGUF model via `llama-cpp-python` (pure C++, no
torch); it's not baked into the production Docker image (Groq needs no
local model at all, so the image stays lean), so locally you'll need:

```bash
cd backend
pip install -r requirements-llm.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

The GGUF file (~260MB) downloads once via `huggingface_hub` on first use
and is cached under `backend/models/` (gitignored). Two things worth
knowing if you go this route, both measured directly while building it:

1. **Vocabulary size dominates a GGUF model's actual RAM cost**, more than
   parameter count or quantization level. `llama.cpp` allocates an
   internal buffer roughly sized `n_ctx * vocab_size`; a model like
   Qwen2.5-0.5B-Instruct with a ~152K-token vocabulary made that buffer
   alone cost ~620MB extra RSS — over Render Free's *entire* 512MB budget
   by itself, regardless of quantization. SmolLM2's ~49K-token vocabulary
   avoids that blowup, which is why it's the default here instead.
2. **Going smaller than ~360M params isn't a free RAM win.** A
   135M-parameter model uses meaningfully less RAM (~170MB vs ~350-450MB)
   but fabricated clinical claims not present in the source text in
   repeated testing (e.g. inventing symptoms) — unacceptable for a medical
   app even with `GroundingValidator` as a backstop. 360M was the smallest
   tier that stayed reliably grounded to its input.

Even at 360M params, on this app's longer multi-section assessment output,
the model sometimes stops after the first section instead of completing
the rewrite — a real capacity limit, not a bug. The same
"did it drop sections / shrink drastically" fallback check protects this
path too, so an under-delivering local model reverts to the deterministic
template text rather than showing an incomplete answer.

Want the biggest local model that still fits comfortably? Any GGUF-format
instruct model works — just point `LLAMACPP_REPO_ID` /
`LLAMACPP_FILENAME` at a different Hugging Face repo/file (small-vocab
models like the SmolLM2/Qwen2.5 families scale most predictably; see the
vocabulary note above before reaching for a big-vocab model). Prefer
`transformers`/torch instead? `MODEL_PROVIDER=local_transformers` +
`pip install -r requirements-full.txt` works the same way. `ollama` is
also available if you have a local Ollama server running.

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
(`0.65·semantic + 0.35·keyword` by default, configurable, retrieving the
top 8 candidates before reranking) with metadata filtering, then reranks
with a deterministic authority/heading-match booster (`app/rag/rerank.py`)
— every source in this build is MedlinePlus/NIH, so the authority
weighting is mostly future-proofing for adding more sources later.

## 6. Safety architecture

- **`EmergencyRiskEngine`** (`app/safety/emergency_engine.py`) — plain
  Python regex + structured-state rules for severe breathing difficulty,
  loss of consciousness, stroke signs, severe chest pain, uncontrolled
  bleeding, anaphylaxis, seizures, suicidal crisis, poisoning, testicular
  torsion, pediatric infant fever, febrile seizure. Runs on **every** turn,
  **before** intake/retrieval/generation — deterministic, not model-judged.
- **`GroundingValidator`** (`app/safety/grounding_validator.py`) — sentence-
  level claim checking against retrieved evidence: embedding similarity,
  a proper-noun/year entailment check, *and* a check for high-stakes
  clinical terms (stroke, tumor, heart attack, sepsis, ...) that must
  already be present in the evidence to survive — added specifically after
  observing a model reach for a scary-but-plausible serious condition that
  was never in the retrieved evidence (topically close enough to pass
  similarity alone). Strips any sentence that fails.
- **`MedicationSafetyEngine`** (`app/safety/medication_safety.py`) — answers
  only from ingested drug chunks; flags allergy conflicts, pregnancy,
  pediatric, and elderly considerations from the patient's profile; refuses
  outright for any drug not in the knowledge base. Deliberately never
  LLM-touched, on any provider — see `app/agents/medication.py`.
- **Prompt/document injection defense** — retrieved chunks and user text are
  always treated as *data*, never as instructions. `template` mode never
  sends retrieved text to a model as an instruction-following prompt at all
  (it just string-formats it). Groq's system prompt is fixed and
  server-controlled — user text and evidence only ever appear inside clearly
  demarcated message content, never concatenated into the instructions
  themselves — and grounding validation runs on its output regardless,
  which is what actually stops an injected instruction from having any
  effect even if the model were tricked into following one.

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
(`useVoice`), `services/` (typed `fetch` wrappers per resource, including
the SSE stream consumer).

Design system: brand teal (`brand-*`) + neutral ink scale, light/dark via
Tailwind's `class` strategy (`stores/themeStore.ts`), rounded cards,
`prose-dr` markdown styling for assistant messages (`react-markdown` +
`remark-gfm`), skeleton/loading-dots states, mobile-first with a bottom nav.

### Real-time streaming & confidence UI

- **Progressive answers:** `chatApi.sendStream` (`services/conversations.ts`)
  consumes `POST /api/chat/stream`'s Server-Sent Events and reveals the
  answer word-group by word-group with a blinking cursor
  (`MessageBubble.tsx`), instead of one blocking wait. This is **not** raw
  model-token streaming — see `app/api/chat.py::_chunk_for_streaming` for
  why: `GroundingValidator` has to see the *complete* model output to
  check it against evidence, so the full pipeline runs first and only the
  already-validated answer is revealed progressively. Same safety
  guarantee as the non-streaming endpoint, still a live, responsive feel.
- **Grounding confidence UI:** every assistant message shows a small
  "X% grounded" badge (how closely the answer's claims matched cited
  sources), and the Assessment panel shows the same figure with an
  explanation plus a per-citation relevance bar — the "won't hallucinate"
  claim is visible in the UI, not just true under the hood.
- **Provider badge:** the header shows which AI actually generated the
  current answer (e.g. "Groq · Llama 3.3 70B"), hidden when running in
  template/fallback mode — transparency about what's answering, not just
  a decorative label.

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

**Want real Groq-powered answers locally?** Add to `backend/.env`:
```bash
MODEL_PROVIDER=groq
GROQ_API_KEY=gsk_...          # free key from https://console.groq.com/keys
```
Leave `MODEL_PROVIDER` unset (or `template`) to run with zero external
dependencies/API calls at all — every feature still works, just with
deterministic evidence-composed answers instead of Groq's natural-language
polish and cross-turn reasoning. See [§4](#4-model-architecture) for the
local-LLM (`llama_cpp`) alternative if you want an offline model instead.

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

**Secrets never go in a committed file.** `GROQ_API_KEY` and `SECRET_KEY`
belong in `backend/.env` locally (gitignored — see `.gitignore`) or as a
Render **secret** environment variable in production (`render.yaml` marks
`GROQ_API_KEY` as `sync: false`, which makes Render prompt for it during
Blueprint deploy rather than storing a real value in the file — see
[§15](#15-render-deployment)). If you ever paste a real key into a chat
log, commit, or issue by mistake, rotate it immediately at
[console.groq.com/keys](https://console.groq.com/keys) — treat it as
compromised the moment it's been typed somewhere outside `.env`.

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
pytest tests/ -q                    # 58 tests: emergency engine, grounding,
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
- `MODEL_PROVIDER=groq` runs generation on Groq's LPU infrastructure —
  zero local CPU/RAM cost regardless of Render plan, and fast even at 70B
  parameters (typical assessment turn: ~2-4s including retrieval +
  grounding validation, measured locally).
- `GET /api/health` responds immediately without waiting on the full
  startup sequence; `GET /api/readiness` separately reports DB/index/model
  status so the app never silently answers with an unready knowledge base.
- `POST /api/chat/stream` (SSE): the full retrieval → generation →
  grounding-validation pipeline runs first (so nothing unvalidated ever
  reaches the client — see §9), then the validated answer is revealed
  progressively for a live, responsive feel instead of one blocking wait.
- Retrieval is capped at `RETRIEVAL_TOP_K` (default 8). Conversation
  history sent to Groq is windowed to the most recent
  `CONVERSATION_HISTORY_TURNS` turns (default 8), not the full raw
  message history, bounding prompt size/latency/cost as a conversation
  grows.
- The knowledge base index ships prebuilt in the Docker image — the
  container never downloads/builds it at boot.

## 17. Security

CORS allowlist (`CORS_ORIGINS`), per-route rate limiting (`slowapi` —
stricter limits on `/api/auth/*` and `/api/voice/*` than `/api/chat`),
Pydantic input validation on every endpoint, bcrypt password hashing,
HTTP-only JWT session cookies with configurable `Secure`/`SameSite`,
security response headers (`X-Frame-Options`, `X-Content-Type-Options`,
`Content-Security-Policy`, `Referrer-Policy`), non-root Docker user,
secrets via environment variables only — never committed to the repo (see
[§12](#12-environment-variables) for how `GROQ_API_KEY` specifically is
handled) — generic error responses (no stack traces leaked — see
`app/main.py` exception handlers). The app is fully functional with **no**
API key configured at all (`MODEL_PROVIDER` defaults to `template`,
zero external calls); `groq` is an explicit opt-in, not a hidden
requirement.

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

- **Groq is a third-party dependency.** The production default
  (`MODEL_PROVIDER=groq`) calls an external API — if Groq has an outage or
  the configured key is invalid, the app automatically falls back to
  `template` (deterministic, evidence-composed, always works) rather than
  erroring, but answers temporarily lose Groq's natural-language polish
  and cross-turn reasoning until it recovers. There's no bundled model
  running inside this app's own container as a backup — that's a
  deliberate trade-off (§4): a locally-hosted model small enough to fit
  typical free-tier RAM budgets was measured to be unreliable enough
  (fabricating clinical claims) to not be a safe default either.
- **`local_transformers`/`ollama`/`llama_cpp` are for local dev, not
  production.** All three are real, wired-up, working providers behind the
  same interface — genuinely useful for testing without an API key — but
  none is the production default; see §4 for the RAM/quality trade-offs
  measured for each.
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
