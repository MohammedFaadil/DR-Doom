from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.conversation import Conversation
from app.models.summary import ConversationSummary
from app.models.user import User
from app.services.pdf import render_summary_pdf

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


def _summary_to_dict(s: ConversationSummary) -> dict:
    return {
        "id": s.id,
        "conversation_id": s.conversation_id,
        "patient_profile": s.patient_profile,
        "primary_concern": s.primary_concern,
        "symptoms": s.symptoms,
        "duration": s.duration,
        "severity": s.severity,
        "associated_symptoms": s.associated_symptoms,
        "relevant_history": s.relevant_history,
        "medications": s.medications,
        "allergies": s.allergies,
        "red_flags": s.red_flags,
        "risk_level": s.risk_level,
        "evidence_consulted": s.evidence_consulted,
        "guidance_provided": s.guidance_provided,
        "recommended_next_step": s.recommended_next_step,
        "unanswered_questions": s.unanswered_questions,
        "disclaimer": s.disclaimer,
        "created_at": s.created_at,
    }


@router.get("")
def list_summaries(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ConversationSummary, Conversation)
        .join(Conversation, Conversation.id == ConversationSummary.conversation_id)
        .filter(Conversation.user_id == user.id)
        .order_by(ConversationSummary.created_at.desc())
        .all()
    )
    return [
        {**_summary_to_dict(s), "conversation_title": c.title}
        for s, c in rows
    ]


def _get_owned_summary(db: Session, user: User, summary_id: str) -> tuple[ConversationSummary, Conversation]:
    row = (
        db.query(ConversationSummary, Conversation)
        .join(Conversation, Conversation.id == ConversationSummary.conversation_id)
        .filter(ConversationSummary.id == summary_id, Conversation.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Summary not found.")
    return row


@router.get("/{summary_id}")
def get_summary(summary_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s, c = _get_owned_summary(db, user, summary_id)
    return {**_summary_to_dict(s), "conversation_title": c.title}


@router.get("/{summary_id}/pdf")
def download_summary_pdf(summary_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s, c = _get_owned_summary(db, user, summary_id)
    pdf_bytes = render_summary_pdf(_summary_to_dict(s), c.title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="dr-doom-summary-{summary_id[:8]}.pdf"'},
    )


@router.delete("/{summary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_summary(summary_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s, _ = _get_owned_summary(db, user, summary_id)
    db.delete(s)
    db.commit()
    return None
