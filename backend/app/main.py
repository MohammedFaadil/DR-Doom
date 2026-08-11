"""
DR DOOM backend entrypoint.

Run locally with:
    uvicorn app.main:app --reload

Render start command (see render.yaml / DEPLOY_RENDER.md):
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import admin, auth, chat, conversations, feedback, health, profile, summary, voice
from app.config import get_settings
from app.core.model_manager import get_model_manager
from app.db import init_db
from app.rag.index_manager import warm_up
from app.utils.limiter import limiter
from app.utils.logging_config import configure_logging
from app.utils.security_headers import SecurityHeadersMiddleware

settings = get_settings()
configure_logging()
logger = logging.getLogger("drdoom")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DR DOOM starting up (environment=%s, model_provider=%s)", settings.ENVIRONMENT, settings.MODEL_PROVIDER)
    init_db()
    warm_up()  # never raises — health/readiness stay honest instead (§70, §76)
    get_model_manager()
    logger.info("DR DOOM startup complete.")
    yield
    logger.info("DR DOOM shutting down.")


app = FastAPI(
    title="DR DOOM API",
    description="Evidence-grounded healthcare RAG assistant — educational, not a diagnostic service.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# IMPORTANT: middleware is applied in reverse order (last added = outermost).
# SecurityHeadersMiddleware uses BaseHTTPMiddleware which can swallow CORS
# preflight headers if it wraps CORSMiddleware. Adding SecurityHeaders first
# means CORSMiddleware runs outermost and handles OPTIONS cleanly.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Professional, non-leaky error messages (§69) — never a raw stack trace.
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": "Invalid request."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Dr Doom ran into an unexpected problem. Please try again."},
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(summary.router)
app.include_router(feedback.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"name": "DR DOOM API", "status": "ok", "docs": "/docs"}
