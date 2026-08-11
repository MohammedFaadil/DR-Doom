from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ConversationSummaryCard(BaseModel):
    id: str
    title: str
    primary_complaint: str | None
    risk_level: str
    is_complete: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    message_type: str
    payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: str
    title: str
    state: str
    risk_level: str
    is_emergency: bool
    is_complete: bool
    patient_state: dict
    messages: list[MessageResponse]

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    answer_question_id: str | None = None
    # Structured answer value for single_select/multi_select/numeric/yes_no/slider
    # questions (e.g. "6-24h", ["nausea", "dyspnea"], 6). `message` stays the
    # human-readable text shown in the chat transcript; `answer_value` (when
    # present) is what actually gets written into patient_state, so a
    # multi_select answer is never accidentally stored as a raw string.
    answer_value: str | int | float | list[str] | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    response_type: str
    message: str
    question: dict | None = None
    evidence: list[dict] = []
    is_emergency: bool = False
    risk_level: str = "unknown"
    conversation_state: str
    model_provider: str = "template"
    summary: dict | None = None
    patient_state: dict = {}
    grounding_confidence: float = 0.0


class FeedbackRequest(BaseModel):
    conversation_id: str | None = None
    was_helpful: bool
    comment: str | None = None
    category: str | None = None


class RenameConversationRequest(BaseModel):
    title: str
