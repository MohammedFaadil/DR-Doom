# DR DOOM backend — optimized for Render Free (§74-77).
#
# The knowledge base index (knowledge_base/index/, chunks/, metadata/) is
# expected to already be built and committed to the repo (run
# `python scripts/ingest_documents.py` locally/in CI and commit the
# output) — this image does NOT rebuild it on every startup or every
# build, per §75 ("do not rebuild vector indexes on startup").
#
# MODEL_PROVIDER defaults to `template` (deterministic, zero extra RAM) —
# measured directly, Render Free's 512MB doesn't have room for any LLM
# alongside this app's existing ~226MB resting footprint (see
# app/core/model_registry.py for the numbers). requirements-llm.txt
# (llama-cpp-python — no torch, ~20-40MB) is still installed below so that
# setting MODEL_PROVIDER=llama_cpp is a genuine one-env-var upgrade on a
# host with more headroom (e.g. Render's paid Starter, 2GB): the GGUF
# model is fetched once via huggingface_hub on first use and cached, no
# image rebuild required. See requirements-full.txt for the heavier
# transformers/torch-based `local_transformers` provider instead, if
# preferred.

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
# llama-cpp-python ships no PyPI wheels (source dist only) — install from
# the maintainer's prebuilt CPU wheel index so the build stays fast and
# compiler-free (see requirements-llm.txt).
COPY requirements.txt requirements-llm.txt .
RUN pip install -r requirements.txt \
    && pip install -r requirements-llm.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

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
