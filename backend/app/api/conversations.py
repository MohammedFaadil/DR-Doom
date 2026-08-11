from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationDetail, ConversationSummaryCard, RenameConversationRequest

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# Greeting / "what can you do" / off-topic turns are recorded so the
# transcript stays coherent, but they aren't consultations — showing them
# in history or counting them in stats would be noise.
NON_CONSULTATION_STATES = ("SMALL_TALK",)


@router.get("", response_model=list[ConversationSummaryCard])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id, Conversation.state.notin_(NON_CONSULTATION_STATES))
        .order_by(desc(Conversation.updated_at))
        .all()
    )


@router.get("/stats/overview")
def conversation_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dashboard counters. Computed with aggregate queries rather than
    loading every conversation, so this stays cheap as history grows."""
    base = db.query(Conversation).filter(
        Conversation.user_id == user.id, Conversation.state.notin_(NON_CONSULTATION_STATES)
    )
    total = base.count()
    completed = base.filter(Conversation.is_complete.is_(True)).count()
    flagged = base.filter(Conversation.is_emergency.is_(True)).count()

    symptom_counts: dict[str, int] = {}
    for (complaint,) in (
        db.query(Conversation.primary_complaint)
        .filter(
            Conversation.user_id == user.id,
            Conversation.primary_complaint.isnot(None),
            Conversation.state.notin_(NON_CONSULTATION_STATES),
        )
        .all()
    ):
        symptom_counts[complaint] = symptom_counts.get(complaint, 0) + 1
    top_concerns = sorted(symptom_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]

    last = base.order_by(desc(Conversation.updated_at)).first()

    return {
        "total_consultations": total,
        "completed": completed,
        "in_progress": total - completed,
        "urgent_flagged": flagged,
        "top_concerns": [{"name": name, "count": count} for name, count in top_concerns],
        "last_consultation_at": last.updated_at if last else None,
    }


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return convo


@router.patch("/{conversation_id}", response_model=ConversationSummaryCard)
def rename_conversation(
    conversation_id: str,
    payload: RenameConversationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    convo.title = payload.title[:120]
    db.commit()
    db.refresh(convo)
    return convo


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.delete(convo)
    db.commit()
    return None
