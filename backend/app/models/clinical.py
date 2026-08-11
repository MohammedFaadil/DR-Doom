from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ClinicalAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One point-in-time structured assessment snapshot produced during a
    conversation (§17-18: evidence -> clinical interpretation -> explanation,
    never LLM -> diagnosis directly)."""

    __tablename__ = "clinical_assessments"

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)

    possible_explanations: Mapped[list] = mapped_column(JSON, default=list)
    red_flags: Mapped[list] = mapped_column(JSON, default=list)
    risk_level: Mapped[str] = mapped_column(String(16), default="unknown")
    grounding_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    missing_information: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)

    conversation = relationship("Conversation", back_populates="assessments")
