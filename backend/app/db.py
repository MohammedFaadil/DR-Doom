"""
Database engine/session setup.

Uses PostgreSQL in production via DATABASE_URL (Render Postgres). Falls back
to a local SQLite file only for local development/tests — see
README.md "Render Free storage constraint": SQLite is NOT persistent on
Render's ephemeral filesystem and must never be relied on in deployment.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they don't exist yet.

    Simplified in place of Alembic migrations for this build (documented
    trade-off in README.md) — fine for a fresh deploy/demo; a real
    production rollout should introduce Alembic before its first schema
    change.
    """
    from app import models  # noqa: F401  (ensure model modules are imported/registered)

    Base.metadata.create_all(bind=engine)
