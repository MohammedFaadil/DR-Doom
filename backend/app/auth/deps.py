from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.config import get_settings
from app.db import get_db
from app.models.user import User

settings = get_settings()


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
    )
    if not session_token:
        raise credentials_error
    user_id = decode_access_token(session_token)
    if not user_id:
        raise credentials_error
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_error
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user


def get_optional_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
) -> User | None:
    if not session_token:
        return None
    user_id = decode_access_token(session_token)
    if not user_id:
        return None
    return db.get(User, user_id)
