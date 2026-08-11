"""
Voice endpoints (§28-29).

The real, always-working default is entirely client-side: the browser's
Web Speech API does speech-to-text directly in the chat composer, and
SpeechSynthesis does text-to-speech for assistant replies — both zero
backend cost, both implemented in the frontend voice hook. This router
exists for the OPTIONAL server-side transcription path (documented in
§92 as intentionally off by default: Render Free cannot host a Whisper
model reliably). When ENABLE_SERVER_TRANSCRIBE=false (the default) this
endpoint returns a clear, honest 501 instead of pretending to transcribe.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.auth.deps import get_current_user
from app.config import get_settings
from app.models.user import User
from app.utils.limiter import limiter

router = APIRouter(prefix="/api/voice", tags=["voice"])
settings = get_settings()


@router.post("/transcribe")
@limiter.limit(settings.RATE_LIMIT_VOICE)
async def transcribe(request: Request, audio: UploadFile = File(...), user: User = Depends(get_current_user)):
    if not settings.ENABLE_SERVER_TRANSCRIBE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Server-side transcription is disabled in this deployment. Dr Doom uses your "
                "browser's built-in speech recognition instead — if that isn't available, please "
                "type your message."
            ),
        )
    # Documented upgrade path: install `faster-whisper` (see requirements-full.txt
    # note in README) and wire it in here. Not enabled by default because a
    # Whisper model does not fit Render Free's memory budget alongside the
    # rest of the app.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Server transcription backend not installed.")
