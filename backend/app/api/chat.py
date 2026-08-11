import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.orchestrator import process_turn
from app.agents.question import find_question_by_id
from app.auth.deps import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models.conversation import Conversation, Message
from app.models.retrieval import Citation, RetrievalLog
from app.models.summary import ConversationSummary
from app.models.user import User
from app.rag.types import RetrievedChunk
from app.schemas.conversation import ChatRequest, ChatResponse
from app.utils.limiter import limiter

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()

_TITLE_WORD_RE = re.compile(r"[a-zA-Z]+")


def _make_title(primary_complaint: str | None, fallback_text: str) -> str:
    base = primary_complaint or fallback_text
    words = _TITLE_WORD_RE.findall(base)[:4]
    title = " ".join(w.capitalize() for w in words) or "New Consultation"
    return f"{title} Assessment" if primary_complaint else title


def _get_or_create_conversation(db: Session, user: User, conversation_id: str | None) -> Conversation:
    if conversation_id:
        convo = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
            .first()
        )
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return convo
    convo = Conversation(user_id=user.id, patient_state={})
    db.add(convo)
    db.flush()
    return convo


def _persist_citations(db: Session, message: Message, evidence: list[RetrievedChunk]) -> list[dict]:
    seen_docs: set[str] = set()
    citation_dicts = []
    for c in evidence:
        if c.chunk.doc_id in seen_docs:
            continue
        seen_docs.add(c.chunk.doc_id)
        citation = Citation(
            message_id=message.id,
            doc_id=c.chunk.doc_id,
            title=c.chunk.title,
            organization=c.chunk.organization,
            url=c.chunk.url,
            relevance_score=c.rerank_score,
        )
        db.add(citation)
        citation_dicts.append(
            {"title": c.chunk.title, "organization": c.chunk.organization, "url": c.chunk.url, "score": c.rerank_score}
        )
    return citation_dicts


def _recent_history(convo: Conversation) -> list[dict]:
    """Snapshot of prior turns as {"role", "content"} dicts for the LLM's
    chat history — must be read BEFORE this turn's new user Message is
    added to the session below, or it would duplicate the current turn.
    Windowed to the most recent CONVERSATION_HISTORY_TURNS turns (each
    turn = 1 user + 1 assistant message) to bound prompt size."""
    window = settings.CONVERSATION_HISTORY_TURNS * 2
    return [{"role": m.role, "content": m.content} for m in convo.messages[-window:] if m.role in ("user", "assistant")]


def _run_turn(db: Session, user: User, payload: ChatRequest) -> tuple[Conversation, ChatResponse]:
    convo = _get_or_create_conversation(db, user, payload.conversation_id)
    is_first_turn = len(convo.messages) == 0
    history = _recent_history(convo)

    db.add(Message(conversation_id=convo.id, role="user", content=payload.message))

    question_obj = find_question_by_id(payload.answer_question_id) if payload.answer_question_id else None
    result = process_turn(
        state=convo.patient_state or {},
        user_text=payload.message,
        answer_question=question_obj,
        answer_value=payload.answer_value,
        is_first_turn=is_first_turn,
        history=history,
    )

    convo.patient_state = result.state
    convo.state = result.conversation_state
    convo.risk_level = result.risk_level
    convo.is_emergency = result.is_emergency
    convo.primary_complaint = result.state.get("primary_complaint") or convo.primary_complaint
    convo.knowledge_version = settings.KNOWLEDGE_VERSION
    convo.model_version = result.model_provider
    convo.prompt_version = settings.PROMPT_VERSION
    if result.response_type in ("assessment", "emergency") or result.summary:
        convo.is_complete = True
    if convo.title == "New consultation" and convo.primary_complaint:
        convo.title = _make_title(convo.primary_complaint, payload.message)

    assistant_message = Message(
        conversation_id=convo.id,
        role="assistant",
        content=result.message,
        message_type=result.response_type,
        payload={"question": result.question} if result.question else None,
    )
    db.add(assistant_message)
    db.flush()

    citation_dicts = _persist_citations(db, assistant_message, result.evidence)

    if result.summary:
        existing = db.query(ConversationSummary).filter(ConversationSummary.conversation_id == convo.id).first()
        if existing:
            db.delete(existing)
            db.flush()
        summary_row = ConversationSummary(conversation_id=convo.id, **result.summary)
        db.add(summary_row)
        db.flush()
        result.summary["id"] = summary_row.id

    db.add(
        RetrievalLog(
            conversation_id=convo.id,
            query=(payload.message or "")[:500],
            top_k=len(result.evidence),
            result_doc_ids=[c.chunk.doc_id for c in result.evidence],
            total_latency_ms=result.retrieval_latency_ms,
            grounding_score=result.grounding_confidence,
            grounding_passed=result.grounding_confidence >= settings.GROUNDING_MIN_SIMILARITY or not result.evidence,
            knowledge_version=settings.KNOWLEDGE_VERSION,
        )
    )

    db.commit()
    db.refresh(convo)

    response = ChatResponse(
        conversation_id=convo.id,
        response_type=result.response_type,
        message=result.message,
        question=result.question,
        evidence=citation_dicts,
        is_emergency=result.is_emergency,
        risk_level=result.risk_level,
        conversation_state=result.conversation_state,
        model_provider=result.model_provider,
        summary=result.summary,
        patient_state=result.state,
        grounding_confidence=result.grounding_confidence,
    )
    return convo, response


@router.post("", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_CHAT)
def chat(request: Request, payload: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, response = _run_turn(db, user, payload)
    return response


_STREAM_CHUNK_WORDS = 3
_STREAM_CHUNK_DELAY_SECONDS = 0.02


def _chunk_for_streaming(text: str) -> list[str]:
    """Split already-finalized text into small word-groups for a
    progressive "typing" reveal in the UI.

    This is NOT raw model token streaming. GroundingValidator has to see
    the model's *complete* output to check every sentence against the
    retrieved evidence and strip anything unsupported (see
    app/safety/grounding_validator.py) — streaming raw tokens straight
    from the model to the browser would mean showing text before it's
    been safety-checked, which defeats the entire "will not hallucinate"
    guarantee this app is built around. So the full pipeline (retrieval ->
    generation -> grounding validation) runs first, exactly as it does for
    the non-streaming endpoint, and only the resulting *validated* text is
    revealed progressively — same safety guarantee, still a live,
    responsive feel instead of one blocking wait.
    """
    words = text.split(" ")
    return [" ".join(words[i : i + _STREAM_CHUNK_WORDS]) for i in range(0, len(words), _STREAM_CHUNK_WORDS)]


@router.post("/stream")
@limiter.limit(settings.RATE_LIMIT_CHAT)
def chat_stream(
    request: Request, payload: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """SSE streaming: status updates while the pipeline runs, then the
    fully validated answer revealed progressively (see
    `_chunk_for_streaming` for why this isn't raw model-token streaming)."""
    import time

    def event_stream():
        yield _sse("status", {"stage": "retrieving", "message": "Retrieving evidence..."})
        _, response = _run_turn(db, user, payload)
        yield _sse("status", {"stage": "preparing", "message": "Preparing response..."})

        for chunk in _chunk_for_streaming(response.message):
            yield _sse("token", {"text": chunk + " "})
            time.sleep(_STREAM_CHUNK_DELAY_SECONDS)

        yield _sse("final", response.model_dump())

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
