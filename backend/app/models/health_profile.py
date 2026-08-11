from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class HealthProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Optional, editable/deletable patient profile. Sensitive fields are
    nullable by design (§21: "do not collect unnecessary personal
    information")."""

    __tablename__ = "health_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)

    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(32), nullable=True)  # male/female/intersex/prefer_not_to_say
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    allergies: Mapped[list] = mapped_column(JSON, default=list)
    known_conditions: Mapped[list] = mapped_column(JSON, default=list)
    medications: Mapped[list] = mapped_column(JSON, default=list)
    medical_history: Mapped[list] = mapped_column(JSON, default=list)

    pregnancy_status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # unknown/pregnant/not_pregnant/na
    lifestyle: Mapped[dict] = mapped_column(JSON, default=dict)
    emergency_contact: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="health_profile")
