"""
Minimal logging setup (§26, §44).

Deliberately does NOT add any request/response body logging middleware —
uvicorn's access log only records method/path/status, never the chat
message body, so conversation content is never written to application
logs by default. Application code must never `logger.info(user_text)` or
log full patient_state; log identifiers (conversation_id, rule_id, latency)
instead.
"""
from __future__ import annotations

import logging

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Keep third-party HTTP client logs at INFO (useful for ingestion) but
    # quiet enough for app runtime.
    logging.getLogger("httpx").setLevel(logging.WARNING)
