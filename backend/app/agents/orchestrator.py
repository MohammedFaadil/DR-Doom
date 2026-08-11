"""
Conversation Orchestrator — the deterministic clinical state machine (§51)
that sequences every agent for one user turn. This is the single place that
decides what happens next; it is intentionally NOT one giant LLM prompt
(§52) — each step below is a separate, auditable, independently-testable
function.

State machine:
  WELCOME -> COMPLAINT_COLLECTION -> RED_FLAG_SCREENING (every turn) ->
  FOLLOW_UP (adaptive questioning) -> EVIDENCE_RETRIEVAL -> ASSESSMENT ->
  GUIDANCE -> SUMMARY -> COMPLETE
  Emergency branch: ANY_STATE -> EMERGENCY -> URGENT_GUIDANCE (terminal for
  the current concern; conversation can still continue for something else)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.explanation import compose_assessment, compose_factual_answer
from app.agents.intake import apply_intake
from app.agents.medication import answer_medication_question
from app.agents.question import apply_answer, record_question_asked, select_next_question
from app.agents.retrieval import retrieve_evidence
from app.agents.scope import classify_scope, no_evidence_message, scope_message
from app.agents.summary import build_summary
from app.clinical.question_bank.bank import Question
from app.rag.index_manager import IndexUnavailable
from app.rag.types import RetrievedChunk
from app.safety.emergency_engine import emergency_guidance_text, screen_for_emergency

INDEX_UNAVAILABLE_MESSAGE = (
    "Medical references are temporarily unavailable, so I can't safely answer right now. "
    "Please try again shortly."
)


@dataclass
class TurnResult:
    state: dict
    conversation_state: str
    response_type: str  # question | text | emergency | assessment | summary | insufficient_evidence
    message: str
    question: Question | None = None
    evidence: list[RetrievedChunk] = field(default_factory=list)
    is_emergency: bool = False
    risk_level: str = "unknown"
    model_provider: str = "template"
    summary: dict | None = None
    retrieval_latency_ms: float = 0.0
    grounding_confidence: float = 0.0


def _estimate_risk_level(state: dict) -> str:
    max_severity = 0
    for s in state.get("symptoms", []):
        sev = s.get("severity")
        if isinstance(sev, (int, float)):
            max_severity = max(max_severity, sev)
    if max_severity >= 8:
        return "urgent"
    if max_severity >= 5:
        return "moderate"
    if state.get("symptoms"):
        return "low"
    return "unknown"


def process_turn(
    state: dict,
    user_text: str,
    answer_question: Question | None = None,
    answer_value: str | int | float | bool | None = None,
    is_first_turn: bool = False,
    history: list[dict] | None = None,
) -> TurnResult:
    working_state = dict(state)

    # 1. Emergency screening — ALWAYS first, regardless of conversation state (§16, §51).
    emergency_matches = screen_for_emergency(user_text, working_state)
    if emergency_matches:
        working_state["red_flags"] = list(
            {*working_state.get("red_flags", []), *[m.rule_id for m in emergency_matches]}
        )
        working_state["risk_level"] = "emergency"
        message = emergency_guidance_text(emergency_matches, country=working_state.get("country", "US"))
        return TurnResult(
            state=working_state,
            conversation_state="EMERGENCY",
            response_type="emergency",
            message=message,
            is_emergency=True,
            risk_level="emergency",
        )

    # 2. Apply the user's input to structured state.
    if answer_question is not None:
        value = answer_value if answer_value is not None else user_text
        working_state = apply_answer(working_state, answer_question, value)
        working_state = record_question_asked(working_state, answer_question["id"])
        # is_answer=True: skip symptom (re-)extraction on the answer's
        # display text — see apply_intake's docstring for why (an option
        # label like "Severe headache" would otherwise be misfiled as a
        # brand-new complaint instead of an associated symptom).
        working_state = apply_intake(working_state, user_text, is_answer=True)
    else:
        working_state = apply_intake(working_state, user_text)

    # 3. Scope triage — only for fresh free-text input with no active
    #    assessment. Answers to questions, and turns where a complaint is
    #    already being worked through, always continue the clinical flow.
    if answer_question is None and not working_state.get("symptoms"):
        scope = classify_scope(user_text)
        if scope != "medical":
            # SMALL_TALK is excluded from history/stats (see
            # app/api/conversations.py) so saying "hi" doesn't leave a
            # meaningless entry in the user's consultation record. If the
            # conversation later moves on to an actual complaint, the state
            # advances and it starts appearing normally.
            return TurnResult(
                state=working_state,
                conversation_state="SMALL_TALK",
                response_type="text",
                message=scope_message(scope),
                risk_level=working_state.get("risk_level", "unknown"),
            )

    intent = working_state.get("intent", "unknown")

    try:
        if intent == "medication_question":
            return _handle_medication(working_state, user_text)
        if intent == "factual_question":
            return _handle_factual(working_state, user_text, history)
        return _handle_symptom_assessment(working_state, user_text, is_first_turn, history)
    except IndexUnavailable:
        return TurnResult(
            state=working_state,
            conversation_state="COMPLETE",
            response_type="insufficient_evidence",
            message=INDEX_UNAVAILABLE_MESSAGE,
        )


def _handle_medication(state: dict, user_text: str) -> TurnResult:
    output = answer_medication_question(user_text, state)
    return TurnResult(
        state=state,
        conversation_state="COMPLETE",
        response_type="text",
        message=output.message,
        evidence=output.evidence,
        risk_level=state.get("risk_level", "unknown"),
        model_provider="template",
    )


def _handle_factual(state: dict, user_text: str, history: list[dict] | None = None) -> TurnResult:
    retrieval = retrieve_evidence(state, user_text)
    output = compose_factual_answer(retrieval, user_text, history)
    response_type = "text" if output.evidence else "insufficient_evidence"
    message = output.message if output.evidence else no_evidence_message(user_text)
    return TurnResult(
        state=state,
        conversation_state="COMPLETE",
        response_type=response_type,
        message=message,
        evidence=output.evidence,
        risk_level=state.get("risk_level", "unknown"),
        model_provider=output.model_provider,
        retrieval_latency_ms=retrieval.total_latency_ms,
        grounding_confidence=output.grounding.confidence,
    )


def _handle_symptom_assessment(
    state: dict, user_text: str, is_first_turn: bool, history: list[dict] | None = None
) -> TurnResult:
    next_question = select_next_question(state)
    if next_question is not None:
        intro = ""
        if is_first_turn:
            intro = (
                "Let's understand this carefully. I'll ask a few focused questions before sharing "
                "any information, so the guidance actually fits your situation.\n\n"
            )
        return TurnResult(
            state=state,
            conversation_state="FOLLOW_UP",
            response_type="question",
            message=intro + next_question["question"],
            question=next_question,
            risk_level=state.get("risk_level", "unknown"),
        )

    # No more questions -> retrieve evidence and produce the assessment.
    retrieval = retrieve_evidence(state, user_text)
    output = compose_assessment(state, retrieval, history)
    risk_level = _estimate_risk_level(state)
    state = dict(state)
    state["risk_level"] = risk_level

    response_type = "assessment" if output.evidence else "insufficient_evidence"
    summary = build_summary(
        state,
        evidence_consulted=[
            {"title": c.chunk.title, "organization": c.chunk.organization, "url": c.chunk.url}
            for c in output.evidence
        ],
        guidance_provided=output.message,
    )

    return TurnResult(
        state=state,
        conversation_state="SUMMARY",
        response_type=response_type,
        message=output.message,
        evidence=output.evidence,
        risk_level=risk_level,
        model_provider=output.model_provider,
        summary=summary,
        retrieval_latency_ms=retrieval.total_latency_ms,
        grounding_confidence=output.grounding.confidence,
    )
