"""
Pydantic schemas for structured clinical state and agent outputs (§12, §53).
All inter-agent JSON is validated through these models — raw model/text
output is never trusted directly.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SymptomState(BaseModel):
    name: str
    severity: int | None = None
    duration: str | None = None
    onset_pattern: str | None = None
    location: str | None = None
    associated_symptoms: list[str] = Field(default_factory=list)
    extra: dict = Field(default_factory=dict)


class PatientState(BaseModel):
    age: float | None = None
    age_unit: Literal["years", "months"] = "years"
    sex: str | None = None
    pregnancy_status: str | None = None
    symptoms: list[SymptomState] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    medical_history: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    risk_level: Literal["unknown", "low", "moderate", "urgent", "emergency"] = "unknown"
    missing_information: list[str] = Field(default_factory=list)
    asked_question_ids: list[str] = Field(default_factory=list)
    primary_complaint: str | None = None
    intent: Literal["symptom_assessment", "factual_question", "medication_question", "unknown"] = "unknown"
    country: str = "US"


class EvidenceItem(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    organization: str
    url: str
    section_heading: str
    text: str
    score: float


class ClinicalResponse(BaseModel):
    """Structured output every agent turn produces before being rendered to
    the user — validated, never freeform (§53)."""

    intent: str
    risk_level: str
    response_type: Literal["question", "text", "emergency", "assessment", "summary", "insufficient_evidence"]
    message: str
    question: dict | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    grounding_confidence: float = 0.0
