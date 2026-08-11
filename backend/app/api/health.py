from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.model_manager import get_model_manager
from app.db import SessionLocal
from app.rag.index_manager import index_is_ready

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/readiness")
def readiness():
    checks = {"database": False, "knowledge_index": False, "model": False}
    errors: dict[str, str] = {}

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = True
    except Exception as exc:  # noqa: BLE001
        errors["database"] = str(exc)

    try:
        checks["knowledge_index"] = index_is_ready()
        if not checks["knowledge_index"]:
            errors["knowledge_index"] = "Index not built yet — run scripts/ingest_documents.py"
    except Exception as exc:  # noqa: BLE001
        errors["knowledge_index"] = str(exc)

    try:
        status_info = get_model_manager().status()
        checks["model"] = True
        checks["model_provider"] = status_info["provider"]
    except Exception as exc:  # noqa: BLE001
        errors["model"] = str(exc)

    overall_ready = checks["database"] and checks["knowledge_index"]
    return {"ready": overall_ready, "checks": checks, "errors": errors}
