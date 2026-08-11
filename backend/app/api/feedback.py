from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.conversation import FeedbackRequest

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", status_code=201)
def submit_feedback(payload: FeedbackRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fb = Feedback(
        conversation_id=payload.conversation_id,
        user_id=user.id,
        was_helpful=payload.was_helpful,
        comment=payload.comment,
        category=payload.category,
    )
    db.add(fb)
    db.commit()
    return {"status": "ok"}
