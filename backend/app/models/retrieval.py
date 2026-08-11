from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RetrievalLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Observability record for one retrieval call (§44, §63). Never stores
    raw medical conversation content — only the rewritten query and scores."""

    __tablename__ = "retrieval_logs"

    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(String(500))
    top_k: Mapped[int] = mapped_column(Integer, default=0)
    result_doc_ids: Mapped[list] = mapped_column(JSON, default=list)
    semantic_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    keyword_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    top_score: Mapped[float] = mapped_column(Float, default=0.0)
    grounding_score: Mapped[float] = mapped_column(Float, default=0.0)
    grounding_passed: Mapped[bool] = mapped_column(default=True)
    knowledge_version: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Citation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "citations"

    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    doc_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(500))
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
