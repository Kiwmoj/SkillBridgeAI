from sqlalchemy import Select, delete, select, update
from sqlalchemy.orm import Session

from apps.backend.models import (
    CONSENT_VERSION,
    ApprovedKnowledge,
    CommunityContribution,
    CommunityPolicy,
    ReviewHistory,
    TrainingConsent,
)


def lock_community_writes(db: Session) -> None:
    # Serialize review, draft, and consent writes across database connections.
    db.execute(update(CommunityPolicy).where(CommunityPolicy.id == 1)
               .values(write_version=CommunityPolicy.write_version + 1))


def get_consent(db: Session, user_id: int) -> TrainingConsent | None:
    return db.query(TrainingConsent).filter_by(user_id=user_id).first()


def has_current_consent(db: Session, user_id: int) -> bool:
    return db.query(TrainingConsent).filter_by(
        user_id=user_id, consent_enabled=True, disclosure_version=CONSENT_VERSION,
    ).first() is not None


def add_consent(db: Session, user_id: int) -> TrainingConsent:
    consent = TrainingConsent(user_id=user_id)
    db.add(consent)
    return consent


def list_consents(db: Session) -> list[TrainingConsent]:
    return db.query(TrainingConsent).all()


def add_contribution(db: Session, **fields) -> CommunityContribution:
    item = CommunityContribution(**fields)
    db.add(item)
    return item


def list_user_contributions(db: Session, user_id: int) -> list[CommunityContribution]:
    return (
        db.query(CommunityContribution).filter_by(user_id=user_id)
        .order_by(CommunityContribution.submitted_at.desc()).all()
    )


def list_all_contributions(db: Session) -> list[CommunityContribution]:
    return db.query(CommunityContribution).order_by(CommunityContribution.submitted_at.desc()).all()


def get_user_contribution(db: Session, user_id: int, contribution_id: int) -> CommunityContribution | None:
    return db.query(CommunityContribution).filter_by(id=contribution_id, user_id=user_id).first()


def get_contribution(db: Session, contribution_id: int) -> CommunityContribution | None:
    return db.get(CommunityContribution, contribution_id)


def user_contribution_ids(user_id: int) -> Select:
    return select(CommunityContribution.id).where(CommunityContribution.user_id == user_id)


def withdraw_user_training_consent(db: Session, user_id: int) -> None:
    db.execute(update(CommunityContribution).where(CommunityContribution.user_id == user_id)
               .values(consent_to_training=False))


def get_approved(db: Session, contribution_id: int) -> ApprovedKnowledge | None:
    return db.query(ApprovedKnowledge).filter_by(source_contribution_id=contribution_id).first()


def add_approved(db: Session, **fields) -> ApprovedKnowledge:
    item = ApprovedKnowledge(**fields)
    db.add(item)
    return item


def count_approved(db: Session) -> int:
    return db.query(ApprovedKnowledge).count()


def add_review(db: Session, contribution_id: int, reviewer_id: int, status: str,
               quality_rating: float | None, notes: str | None) -> ReviewHistory:
    item = ReviewHistory(contribution_id=contribution_id, reviewer_id=reviewer_id, status=status,
                         quality_rating=quality_rating, notes=notes)
    db.add(item)
    return item


def list_reviews(db: Session, contribution_id: int) -> list[ReviewHistory]:
    return (
        db.query(ReviewHistory).filter_by(contribution_id=contribution_id)
        .order_by(ReviewHistory.created_at.desc()).all()
    )


def delete_user_community_rows(db: Session, user_id: int) -> None:
    """Remove approved copies and review history derived from the user's contributions, then the contributions."""
    items = user_contribution_ids(user_id)
    db.execute(delete(ApprovedKnowledge).where(ApprovedKnowledge.source_contribution_id.in_(items)))
    db.execute(delete(ReviewHistory).where(ReviewHistory.contribution_id.in_(items)))
    db.execute(delete(CommunityContribution).where(CommunityContribution.user_id == user_id))
