from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120), default="New consultation")
    primary_complaint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Clinical state machine position — see app/clinical/state_machine.py
    state: Mapped[str] = mapped_column(String(32), default="WELCOME", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)  # low/moderate/urgent/emergency
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Structured clinical/patient state accumulated across the conversation
    # (age, sex, symptoms[], medications, allergies, red_flags, missing_information, ...)
    patient_state: Mapped[dict] = mapped_column(JSON, default=dict)

    knowledge_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    summary = relationship(
        "ConversationSummary", back_populates="conversation", uselist=False, cascade="all, delete-orphan"
    )
    assessments = relationship("ClinicalAssessment", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)

    # For assistant messages: interactive question payload, citations, etc.
    message_type: Mapped[str] = mapped_column(String(32), default="text")  # text|question|emergency|assessment|summary
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
