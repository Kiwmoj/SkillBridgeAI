from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from apps.backend.models import (
    AIUsage,
    CustomOccupation,
    LearningActivity,
    Opportunity,
    Portfolio,
    Profile,
    Project,
    Roadmap,
    SavedCareer,
    SkillAssessment,
    TrainingConsent,
    User,
)

USER_OWNED_TABLES = (TrainingConsent, AIUsage, SkillAssessment, LearningActivity, Roadmap, Project,
                     Portfolio, Opportunity, CustomOccupation, SavedCareer)


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter_by(email=email.lower()).first()


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def add_user(db: Session, email: str, name: str, password_hash: str, role: str = "student") -> User:
    user = User(email=email.lower(), name=name, password_hash=password_hash, role=role)
    user.profile = Profile()
    db.add(user)
    return user


def revoke_sessions(db: Session, user_id: int) -> None:
    db.execute(update(User).where(User.id == user_id).values(session_version=User.session_version + 1))


def apply_password_reset(db: Session, user_id: int, recovery_digest: str, password_hash: str) -> int:
    """Reset the password only if the recovery digest still matches; return the affected row count."""
    result = db.execute(
        update(User).where(User.id == user_id, User.recovery_hash == recovery_digest).values(
            password_hash=password_hash, recovery_hash=None, session_version=User.session_version + 1,
        )
    )
    return result.rowcount


def get_profile(db: Session, user_id: int) -> Profile | None:
    return db.query(Profile).filter_by(user_id=user_id).first()


def add_profile(db: Session, user_id: int) -> Profile:
    profile = Profile(user_id=user_id)
    db.add(profile)
    return profile


def delete_user_records(db: Session, user: User) -> None:
    """Delete every row owned by the user, then the user; community rows are removed by their own repository."""
    for table in USER_OWNED_TABLES:
        db.execute(delete(table).where(table.user_id == user.id))
    db.delete(user)
