"""
Pluggable generation-provider registry (§3, §47, §77).

Every provider implements the same narrow interface: given already-composed,
evidence-grounded section text, optionally *rephrase* it in plainer
language. Providers are NEVER asked to invent new medical facts — the
sections themselves are built deterministically by
app/agents/explanation.py from retrieved evidence + structured patient
state (§17: evidence -> clinical interpretation -> explanation, not
LLM -> diagnosis). The GroundingValidator (app/safety/grounding_validator.py)
re-checks whatever a provider returns before it ever reaches the user, so
even LOCAL_TRANSFORMERS mode cannot introduce ungrounded claims that survive.

Providers:
  * template            deterministic, zero extra RAM/CPU, always available.
                         Returns the composed text unchanged. The default —
                         see below for why — and the ModelManager's own
                         fallback if a heavier provider fails.
  * llama_cpp            quantized GGUF model via llama.cpp (needs
                         requirements-llm.txt), lazy-loaded on first use, no
                         torch dependency. Real measurement on the default
                         model (SmolLM2-360M-Instruct, chosen for its small
                         ~49K-token vocabulary — see LlamaCppProvider) adds
                         ~350-450MB RSS on top of this app's ~226MB
                         resting footprint (embeddings + FAISS + FastAPI +
                         DB pool) — i.e. 600-670MB total, over Render
                         Free's 512MB. Good fit for Render's paid Starter
                         tier (2GB) or any host with >768MB free.
  * local_transformers   small local HF instruct model via `transformers`
                         (needs requirements-full.txt, includes torch —
                         ~2GB+ RSS even for a 0.5B model in fp32). Useful
                         for local dev on a machine with real RAM; heavier
                         than llama_cpp for equivalent output quality.
  * ollama               calls a locally-running Ollama server over HTTP.

`template` is the default because it is the only provider guaranteed to
run within Render Free's 512MB alongside the rest of this app — see
README.md for the measured numbers behind that call. Swap providers purely
via MODEL_PROVIDER in the environment — no code changes required anywhere
else in the app.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import Settings

logger = logging.getLogger("drdoom.model")


class GenerationProvider(ABC):
    name: str = "base"

    @abstractmethod
    def rephrase(self, composed_text: str, *, style: str = "plain") -> str:
        """Optionally rewrite already-grounded, already-composed text in
        plainer/more conversational language. Must not add new claims —
        callers still run the GroundingValidator afterward regardless."""
        raise NotImplementedError

    def is_available(self) -> bool:
        return True


class TemplateProvider(GenerationProvider):
    """Deterministic pass-through. The 'model' here is the structured
    template composer itself — see app/agents/explanation.py. This is the
    honest default when no LLM can safely fit in the deployment's RAM."""

    name = "template"

    def rephrase(self, composed_text: str, *, style: str = "plain") -> str:
        return composed_text


_REPHRASE_SYSTEM_PROMPT = (
    "You are a rewriting assistant inside a medical information app. You will be given an "
    "already-written, evidence-based clinical note. Rewrite it in clear, warm, plain language "
    "for a patient to read, keeping it concise.\n"
    "Strict rules:\n"
    "- Output ONLY the rewritten note itself. Never mention that you rewrote it, never describe "
    "what you changed, never add an intro or closing sentence of your own — the very first "
    "character of your reply must be the start of the rewritten note.\n"
    "- Never add a fact, number, drug name, condition, or claim that is not already present "
    "in the note. In particular, never name a specific serious condition (e.g. stroke, tumor, "
    "heart attack) unless that exact word already appears in the note.\n"
    "- Never remove a warning or disclaimer.\n"
    "- Keep every markdown heading EXACTLY as given, character-for-character including the "
    "leading '##' — do not convert a heading to bold text, and do not reword it.\n"
    "- Do not add new sections, new headings, or a new closing summary.\n"
    "- If unsure how to improve a sentence, leave it as-is rather than guessing."
)


class LlamaCppProvider(GenerationProvider):
    """Quantized GGUF instruct model via llama.cpp (`llama-cpp-python`) —
    pure C++ inference, no torch dependency (§ requirements-llm.txt). Off
    by default; lazy-loaded on first use so app startup/health checks never
    block on it.

    Model choice matters more than it looks. Two things were measured
    directly while building this, not assumed:
      1. llama.cpp allocates an internal logits buffer sized roughly
         n_ctx * vocab_size. Qwen2.5-0.5B-Instruct's ~152K-token
         vocabulary made that buffer alone cost ~620MB extra RSS at
         n_ctx=1024 — enough by itself to exceed Render Free's entire
         512MB. SmolLM2 (the default here) has a ~49K-token vocabulary,
         avoiding that blowup.
      2. Going smaller than SmolLM2-360M isn't free: SmolLM2-135M-Instruct
         uses far less RAM (~170MB delta vs ~350-450MB) but fabricated
         clinical claims not present in the source text in repeated
         testing ("nausea and vomiting during sleep attacks", invented
         wholesale) — unacceptable for a medical app even with
         GroundingValidator as a backstop. 360M was the smallest tier that
         stayed reliably grounded to its input across repeated trials.

    Net result: ~350-450MB RSS on top of this app's ~226MB resting
    footprint. That doesn't fit Render Free (512MB) — template is the
    default there — but is a comfortable fit for Render's paid Starter
    tier (2GB) or any host with real headroom.

    The GGUF file is expected to already be baked into the deployment
    image at LLAMACPP_MODEL_PATH (see Dockerfile) — consistent with how
    the knowledge base index is prebuilt and shipped rather than
    downloaded at boot. If it isn't there (e.g. local dev without running
    the download step), this falls back to downloading it once via
    huggingface_hub and caching it at that same path.
    """

    name = "llama_cpp"

    def __init__(
        self,
        model_path: str,
        repo_id: str,
        filename: str,
        n_ctx: int,
        n_threads: int,
        max_tokens: int,
        temperature: float,
        n_batch: int = 128,
    ) -> None:
        self.model_path = model_path
        self.repo_id = repo_id
        self.filename = filename
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.max_tokens = max_tokens
        self.temperature = temperature
        # NOT the same as n_ctx: llama.cpp allocates a logits buffer sized
        # n_batch * vocab_size, and Qwen's ~152K-token vocab makes that
        # buffer huge if n_batch is set as large as n_ctx (measured: 1024 ->
        # ~620MB extra RSS on this exact model, enough alone to blow
        # Render Free's 512MB budget). A short rephrase prompt doesn't need
        # large-batch prompt processing, so keep this small.
        self.n_batch = n_batch
        self._llm = None
        self._load_failed = False

    def _resolve_model_path(self) -> str | None:
        path = Path(self.model_path)
        if path.exists():
            return str(path)
        try:
            from huggingface_hub import hf_hub_download  # type: ignore

            logger.info("GGUF model not found at %s; downloading %s/%s ...", path, self.repo_id, self.filename)
            path.parent.mkdir(parents=True, exist_ok=True)
            return hf_hub_download(repo_id=self.repo_id, filename=self.filename, local_dir=str(path.parent))
        except Exception:  # noqa: BLE001
            logger.exception("Could not download GGUF model %s/%s", self.repo_id, self.filename)
            return None

    def _ensure_loaded(self) -> bool:
        if self._llm is not None:
            return True
        if self._load_failed:
            return False
        resolved = self._resolve_model_path()
        if not resolved:
            self._load_failed = True
            return False
        try:
            from llama_cpp import Llama  # type: ignore

            logger.info(
                "Loading llama.cpp model from %s (n_ctx=%d, n_batch=%d, n_threads=%d) ...",
                resolved, self.n_ctx, self.n_batch, self.n_threads,
            )
            self._llm = Llama(
                model_path=resolved,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_batch=self.n_batch,
                n_ubatch=self.n_batch,
                verbose=False,
            )
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load LLAMA_CPP model at %s; falling back to template.", resolved)
            self._load_failed = True
            return False

    def is_available(self) -> bool:
        return self._ensure_loaded()

    def rephrase(self, composed_text: str, *, style: str = "plain") -> str:
        if not self._ensure_loaded():
            return composed_text
        try:
            out = self._llm.create_chat_completion(  # type: ignore[union-attr]
                messages=[
                    {"role": "system", "content": _REPHRASE_SYSTEM_PROMPT},
                    {"role": "user", "content": composed_text},
                ],
                max_tokens=self.max_tokens,
                temperature=max(self.temperature, 0.0),
                top_p=0.9,
                # Small instruct models loop/repeat without this — measured
                # directly: SmolLM2-360M without repeat_penalty degenerates
                # into repeating whole sections verbatim within ~150 tokens.
                repeat_penalty=1.3,
            )
            text = out["choices"][0]["message"]["content"].strip()
            return text or composed_text
        except Exception:  # noqa: BLE001
            logger.exception("LLAMA_CPP generation failed; returning template text unchanged.")
            return composed_text


class LocalTransformersProvider(GenerationProvider):
    """Small local instruct model via `transformers`. Off by default — see
    requirements-full.txt. Lazy-loaded so app startup never blocks on it."""

    name = "local_transformers"

    def __init__(self, model_name: str, max_tokens: int, temperature: float) -> None:
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._pipeline = None
        self._load_failed = False

    def _ensure_loaded(self) -> bool:
        if self._pipeline is not None:
            return True
        if self._load_failed:
            return False
        try:
            from transformers import pipeline  # type: ignore

            logger.info("Loading local transformers model %s ...", self.model_name)
            self._pipeline = pipeline("text-generation", model=self.model_name, device_map="cpu")
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load LOCAL_TRANSFORMERS model %s; falling back to template.", self.model_name)
            self._load_failed = True
            return False

    def is_available(self) -> bool:
        return self._ensure_loaded()

    def rephrase(self, composed_text: str, *, style: str = "plain") -> str:
        if not self._ensure_loaded():
            return composed_text
        # Instruct models are tuned against their chat template — sending a
        # raw completion-style prompt (as opposed to proper role-tagged
        # messages) measurably degrades instruction-following, which is
        # exactly the failure mode this method exists to avoid.
        messages = [
            {"role": "system", "content": _REPHRASE_SYSTEM_PROMPT},
            {"role": "user", "content": composed_text},
        ]
        try:
            out = self._pipeline(  # type: ignore[operator]
                messages,
                max_new_tokens=self.max_tokens,
                temperature=max(self.temperature, 0.01),
                do_sample=self.temperature > 0,
                return_full_text=False,
            )
            generated = out[0]["generated_text"]
            # Some `transformers` versions return the full chat history as a
            # list of role dicts even with return_full_text=False; others
            # return a plain string. Handle both.
            if isinstance(generated, list):
                text = generated[-1].get("content", "") if generated else ""
            else:
                text = generated
            return text.strip() or composed_text
        except Exception:  # noqa: BLE001
            logger.exception("LOCAL_TRANSFORMERS generation failed; returning template text unchanged.")
            return composed_text


class OllamaProvider(GenerationProvider):
    """Calls a locally-running Ollama server (documented provider stub —
    only usable if the operator has Ollama installed and running; not part
    of the default deployment path)."""

    name = "ollama"

    def __init__(self, base_url: str, model_name: str, max_tokens: int, temperature: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def is_available(self) -> bool:
        try:
            import httpx

            r = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    def rephrase(self, composed_text: str, *, style: str = "plain") -> str:
        try:
            import httpx

            prompt = (
                "Rewrite the following clinical information note in clear, plain language. "
                "Do not add new facts. Keep all warnings.\n\n" + composed_text
            )
            r = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
                },
                timeout=30.0,
            )
            r.raise_for_status()
            return r.json().get("response", "").strip() or composed_text
        except Exception:  # noqa: BLE001
            logger.exception("Ollama generation failed; returning template text unchanged.")
            return composed_text


def build_provider(settings: Settings) -> GenerationProvider:
    if settings.MODEL_PROVIDER == "llama_cpp":
        return LlamaCppProvider(
            settings.LLAMACPP_MODEL_PATH,
            settings.LLAMACPP_REPO_ID,
            settings.LLAMACPP_FILENAME,
            settings.LLAMACPP_CTX,
            settings.LLAMACPP_THREADS,
            settings.MODEL_MAX_TOKENS,
            settings.MODEL_TEMPERATURE,
            n_batch=settings.LLAMACPP_BATCH,
        )
    if settings.MODEL_PROVIDER == "local_transformers":
        return LocalTransformersProvider(settings.MODEL_NAME, settings.MODEL_MAX_TOKENS, settings.MODEL_TEMPERATURE)
    if settings.MODEL_PROVIDER == "ollama":
        return OllamaProvider(settings.OLLAMA_BASE_URL, settings.MODEL_NAME, settings.MODEL_MAX_TOKENS, settings.MODEL_TEMPERATURE)
    return TemplateProvider()
