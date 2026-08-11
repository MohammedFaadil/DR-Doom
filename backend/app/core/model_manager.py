"""
ModelManager (§47): owns the active GenerationProvider, retries, and falls
back to TemplateProvider if the configured provider fails to load or
errors at call time. Never returns fabricated content just because a model
failed — worst case it returns the deterministic template text untouched.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.config import Settings, get_settings
from app.core.model_registry import GenerationProvider, TemplateProvider, build_provider

logger = logging.getLogger("drdoom.model")


class ModelManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._primary: GenerationProvider = build_provider(settings)
        self._fallback: GenerationProvider = TemplateProvider()

    @property
    def active_provider_name(self) -> str:
        return self._primary.name

    def rephrase(self, composed_text: str, *, style: str = "plain") -> tuple[str, str]:
        """Returns (text, provider_used_name)."""
        if self._primary.name == "template":
            return self._primary.rephrase(composed_text, style=style), "template"
        try:
            if not self._primary.is_available():
                logger.warning("Provider %s unavailable; using template fallback.", self._primary.name)
                return self._fallback.rephrase(composed_text, style=style), "template_fallback"
            result = self._primary.rephrase(composed_text, style=style)
            if not result or not result.strip():
                return self._fallback.rephrase(composed_text, style=style), "template_fallback"
            return result, self._primary.name
        except Exception:  # noqa: BLE001
            logger.exception("Provider %s raised during rephrase(); using template fallback.", self._primary.name)
            return self._fallback.rephrase(composed_text, style=style), "template_fallback"

    def supports_full_generation(self) -> bool:
        """True only when the active provider can compose an answer
        directly from evidence + conversation history (currently: Groq)
        and is actually usable right now (e.g. GROQ_API_KEY is set)."""
        return self._primary.supports_full_generation and self._primary.is_available()

    def generate_answer(self, system_prompt: str, messages: list[dict], *, max_tokens: int | None = None) -> str | None:
        """Returns the generated answer, or None if generation wasn't
        possible/failed — callers (see explanation.py) must fall back to
        the deterministic template composer in that case, same pattern as
        every other failure mode in this class."""
        try:
            return self._primary.generate_answer(system_prompt, messages, max_tokens=max_tokens)
        except Exception:  # noqa: BLE001
            logger.exception("Provider %s raised during generate_answer().", self._primary.name)
            return None

    def status(self) -> dict:
        model_name = self.settings.GROQ_MODEL if self._primary.name == "groq" else self.settings.MODEL_NAME
        return {
            "provider": self._primary.name,
            "model_name": model_name if self._primary.name != "template" else "deterministic-template",
            "available": self._primary.is_available() if self._primary.name != "template" else True,
        }


@lru_cache
def get_model_manager() -> ModelManager:
    return ModelManager(get_settings())
