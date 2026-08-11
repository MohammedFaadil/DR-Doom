from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ConversationSummary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversation_summaries"

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, index=True
    )

    patient_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    primary_concern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symptoms: Mapped[list] = mapped_column(JSON, default=list)
    duration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    associated_symptoms: Mapped[list] = mapped_column(JSON, default=list)
    relevant_history: Mapped[list] = mapped_column(JSON, default=list)
    medications: Mapped[list] = mapped_column(JSON, default=list)
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    red_flags: Mapped[list] = mapped_column(JSON, default=list)
    risk_level: Mapped[str] = mapped_column(String(16), default="unknown")
    evidence_consulted: Mapped[list] = mapped_column(JSON, default=list)  # citation dicts
    guidance_provided: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    unanswered_questions: Mapped[list] = mapped_column(JSON, default=list)
    disclaimer: Mapped[str] = mapped_column(Text)

    conversation = relationship("Conversation", back_populates="summary")
