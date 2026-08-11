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

    def status(self) -> dict:
        return {
            "provider": self._primary.name,
            "model_name": self.settings.MODEL_NAME if self._primary.name != "template" else "deterministic-template",
            "available": self._primary.is_available() if self._primary.name != "template" else True,
        }


@lru_cache
def get_model_manager() -> ModelManager:
    return ModelManager(get_settings())
