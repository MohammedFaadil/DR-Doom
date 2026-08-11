"""
Admin diagnostics dashboard (§43-44). Protected by get_current_admin.
Reads real DB-backed metrics — never fabricated numbers — and exposes no
patient-identifying conversation content, only aggregate operational data.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.deps import get_current_admin
from app.config import get_settings
from app.db import get_db
from app.models.feedback import Feedback
from app.models.retrieval import RetrievalLog
from app.models.user import User
from app.rag.index_manager import index_is_ready
from app.core.model_manager import get_model_manager

router = APIRouter(prefix="/api/admin", tags=["admin"])
settings = get_settings()


@router.get("/overview")
def overview(_: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    manifest_path = Path(settings.VECTOR_INDEX_PATH).parent / "metadata" / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    total_queries = db.query(func.count(RetrievalLog.id)).scalar() or 0
    avg_latency = db.query(func.avg(RetrievalLog.total_latency_ms)).scalar() or 0.0
    avg_grounding = db.query(func.avg(RetrievalLog.grounding_score)).scalar() or 0.0
    grounding_failures = db.query(func.count(RetrievalLog.id)).filter(RetrievalLog.grounding_passed.is_(False)).scalar() or 0

    feedback_total = db.query(func.count(Feedback.id)).scalar() or 0
    feedback_positive = db.query(func.count(Feedback.id)).filter(Feedback.was_helpful.is_(True)).scalar() or 0

    return {
        "knowledge_base": {
            "version": settings.KNOWLEDGE_VERSION,
            "document_count": manifest.get("document_count", 0),
            "chunk_count": manifest.get("chunk_count", 0),
            "generated_at": manifest.get("generated_at"),
            "index_ready": index_is_ready(),
        },
        "model": get_model_manager().status(),
        "retrieval_metrics": {
            "total_queries": total_queries,
            "avg_latency_ms": round(float(avg_latency), 1),
            "avg_grounding_score": round(float(avg_grounding), 3),
            "grounding_failures": grounding_failures,
        },
        "feedback": {
            "total": feedback_total,
            "positive": feedback_positive,
            "positive_rate": round(feedback_positive / feedback_total, 3) if feedback_total else None,
        },
        "config": {
            "embedding_model": settings.EMBEDDING_MODEL,
            "hybrid_semantic_weight": settings.HYBRID_SEMANTIC_WEIGHT,
            "hybrid_keyword_weight": settings.HYBRID_KEYWORD_WEIGHT,
            "grounding_min_similarity": settings.GROUNDING_MIN_SIMILARITY,
            "environment": settings.ENVIRONMENT,
        },
    }


@router.get("/retrieval-logs")
def retrieval_logs(limit: int = 50, _: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(RetrievalLog).order_by(RetrievalLog.created_at.desc()).limit(min(limit, 200)).all()
    return [
        {
            "id": r.id,
            "query": r.query,
            "top_k": r.top_k,
            "total_latency_ms": r.total_latency_ms,
            "grounding_score": r.grounding_score,
            "grounding_passed": r.grounding_passed,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/feedback")
def feedback_list(limit: int = 50, _: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(Feedback).order_by(Feedback.created_at.desc()).limit(min(limit, 200)).all()
    return [
        {
            "id": f.id,
            "was_helpful": f.was_helpful,
            "comment": f.comment,
            "category": f.category,
            "created_at": f.created_at,
        }
        for f in rows
    ]
