from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ConsentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "consent_records"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    consent_type: Mapped[str] = mapped_column(String(64))  # e.g. "terms", "data_processing", "voice"
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[str] = mapped_column(String(16), default="1.0")

    user = relationship("User", back_populates="consent_records")
