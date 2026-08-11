from __future__ import annotations

from pydantic import BaseModel


class HealthProfileUpdate(BaseModel):
    age: int | None = None
    sex: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    allergies: list[str] | None = None
    known_conditions: list[str] | None = None
    medications: list[str] | None = None
    medical_history: list[str] | None = None
    pregnancy_status: str | None = None
    lifestyle: dict | None = None
    emergency_contact: dict | None = None


class HealthProfileResponse(BaseModel):
    id: str
    age: int | None
    sex: str | None
    height_cm: float | None
    weight_kg: float | None
    allergies: list
    known_conditions: list
    medications: list
    medical_history: list
    pregnancy_status: str | None
    lifestyle: dict
    emergency_contact: dict | None

    model_config = {"from_attributes": True}
