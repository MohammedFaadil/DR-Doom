from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.health_profile import HealthProfile
from app.models.user import User
from app.schemas.profile import HealthProfileResponse, HealthProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _get_or_create_profile(db: Session, user: User) -> HealthProfile:
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user.id).first()
    if not profile:
        profile = HealthProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=HealthProfileResponse)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_or_create_profile(db, user)


@router.put("", response_model=HealthProfileResponse)
def update_profile(
    payload: HealthProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    profile = _get_or_create_profile(db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """§21/§26: users can delete their sensitive health data at will."""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user.id).first()
    if profile:
        db.delete(profile)
        db.commit()
    return None
