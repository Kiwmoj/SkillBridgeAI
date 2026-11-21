"""User profile reads and updates."""
from sqlalchemy.orm import Session

from apps.backend.models import User
from apps.backend.repositories import users as repository
from apps.backend.schemas.profiles import ProfileRequest


def get_profile(db: Session, user: User):
    profile = repository.get_profile(db, user.id)
    if not profile:
        return {"id": None, "user_id": user.id}
    return profile


def update_profile(db: Session, user: User, request: ProfileRequest):
    profile = repository.get_profile(db, user.id) or repository.add_profile(db, user.id)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
