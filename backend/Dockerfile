# DR DOOM backend — production deploy runs on Groq (MODEL_PROVIDER=groq,
# see render.yaml + app/core/model_registry.py::GroqProvider). Groq is a
# hosted API reachable over plain HTTPS (via `httpx`, already in
# requirements.txt) — no extra ML dependencies, no local model weights, no
# torch, so this image stays small and the build stays fast regardless of
# which Render plan you're on.
#
# The knowledge base index (knowledge_base/index/, chunks/, metadata/) is
# expected to already be built and committed to the repo (run
# `python scripts/ingest_documents.py` locally/in CI and commit the
# output) — this image does NOT rebuild it on every startup or every
# build, per §75 ("do not rebuild vector indexes on startup").
#
# Testing locally without a Groq key? MODEL_PROVIDER=template (zero
# dependencies, always works) or MODEL_PROVIDER=llama_cpp (needs
# `pip install -r requirements-llm.txt`, not installed in this image — see
# README.md "Local model testing") both work as drop-in swaps, no code
# changes, but are meant for local dev, not this deploy image.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps needed by faiss-cpu / lxml / reportlab at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code + the prebuilt knowledge base artifacts.
COPY app ./app
COPY scripts ./scripts
COPY evaluation ./evaluation
COPY knowledge_base/index ./knowledge_base/index
COPY knowledge_base/chunks ./knowledge_base/chunks
COPY knowledge_base/metadata ./knowledge_base/metadata

# Non-root user (§74).
RUN useradd --create-home --uid 1000 drdoom \
    && chown -R drdoom:drdoom /app
USER drdoom

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",8000)}/api/health', timeout=3)" || exit 1

# Render supplies $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
