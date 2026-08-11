"""
Central application configuration.

Every tunable in the system (database, model provider, retrieval weights,
feature flags) is read from environment variables here — nothing below is
hardcoded elsewhere in the app. See /.env.example for the full list with
explanations.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str = f"sqlite:///{BACKEND_ROOT / 'drdoom_dev.db'}"

    # --- Security ---
    SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_SECURE: bool = False  # set true in production (HTTPS)
    COOKIE_NAME: str = "drdoom_session"
    # "lax" works for same-site local dev (see frontend/vite.config.ts proxy).
    # Render deploys the frontend Static Site and backend Web Service on
    # different subdomains, which browsers treat as cross-site — that
    # requires COOKIE_SAMESITE=none (and COOKIE_SECURE=true, which "none"
    # requires anyway). Set both in the backend's Render environment vars.
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Model layer ---
    MODEL_PROVIDER: Literal["template", "local_transformers", "ollama"] = "template"
    MODEL_NAME: str = "Qwen/Qwen2.5-0.5B-Instruct"
    MODEL_QUANTIZATION: str = "none"
    MODEL_MAX_TOKENS: int = 512
    MODEL_TEMPERATURE: float = 0.2
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- Embeddings / retrieval ---
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    VECTOR_INDEX_PATH: str = str(BACKEND_ROOT / "knowledge_base" / "index")
    HYBRID_SEMANTIC_WEIGHT: float = 0.70
    HYBRID_KEYWORD_WEIGHT: float = 0.30
    RETRIEVAL_TOP_K: int = 6
    GROUNDING_MIN_SIMILARITY: float = 0.42

    KNOWLEDGE_VERSION: str = "2026.08.1"
    PROMPT_VERSION: str = "1.0.0"

    # --- Feature flags ---
    ENABLE_VOICE: bool = True
    ENABLE_TTS: bool = True
    ENABLE_SERVER_TRANSCRIBE: bool = False

    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"

    # --- Rate limiting ---
    RATE_LIMIT_CHAT: str = "30/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_VOICE: str = "15/minute"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
