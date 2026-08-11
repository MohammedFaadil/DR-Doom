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
                         Returns the composed text unchanged. Default and
                         recommended for Render Free.
  * local_transformers   small local HF instruct model (needs
                         requirements-full.txt), lazy-loaded on first use.
  * ollama               calls a locally-running Ollama server over HTTP.

Swap providers purely via MODEL_PROVIDER in the environment — no code
changes required anywhere else in the app.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

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
        prompt = (
            "Rewrite the following clinical information note in clear, plain, reassuring "
            "language for a patient. Do not add any new facts, numbers, drug names, or "
            "claims that are not already present. Keep every warning and disclaimer. "
            "Keep section headings.\n\n---\n" + composed_text + "\n---\nRewritten version:"
        )
        try:
            out = self._pipeline(  # type: ignore[operator]
                prompt, max_new_tokens=self.max_tokens, temperature=max(self.temperature, 0.01), do_sample=self.temperature > 0
            )
            text = out[0]["generated_text"]
            rewritten = text.split("Rewritten version:", 1)[-1].strip()
            return rewritten or composed_text
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
    if settings.MODEL_PROVIDER == "local_transformers":
        return LocalTransformersProvider(settings.MODEL_NAME, settings.MODEL_MAX_TOKENS, settings.MODEL_TEMPERATURE)
    if settings.MODEL_PROVIDER == "ollama":
        return OllamaProvider(settings.OLLAMA_BASE_URL, settings.MODEL_NAME, settings.MODEL_MAX_TOKENS, settings.MODEL_TEMPERATURE)
    return TemplateProvider()
