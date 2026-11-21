"""Community knowledge: submissions, per-contribution and account-level training consent, moderation."""
import json

from sqlalchemy.orm import Session

from apps.backend.core.exceptions import BadRequest, NotFoundError, ValidationFailure
from apps.backend.database.base import utcnow
from apps.backend.models import CONSENT_VERSION, CommunityContribution, User
from apps.backend.repositories import community as repository
from apps.backend.schemas.community import ContributionRequest, ContributionReviewRequest, TrainingConsentRequest
from apps.backend.services.ai.retrieval import hashed_embedding
from apps.backend.services.community.privacy import contains_identifiers
from apps.backend.services.training.pipeline import invalidate_datasets

MINIMUM_APPROVAL_RATING = 3


def consent_summary(db: Session, user_id: int) -> dict | object:
    consent = repository.get_consent(db, user_id)
    if not consent:
        return {"consent_enabled": False, "disclosure_version": CONSENT_VERSION, "withdrawn_at": None}
    return consent


def update_consent(db: Session, user_id: int, request: TrainingConsentRequest):
    repository.lock_community_writes(db)
    consent = repository.get_consent(db, user_id) or repository.add_consent(db, user_id)
    consent.consent_enabled = request.consent_enabled
    consent.disclosure_version = request.disclosure_version
    consent.updated_at = utcnow()
    consent.withdrawn_at = None if request.consent_enabled else utcnow()
    if not request.consent_enabled:
        # Withdrawal revokes every pending permission and any draft built from this user's contributions.
        invalidate_datasets(db, repository.user_contribution_ids(user_id))
        repository.withdraw_user_training_consent(db, user_id)
    db.commit()
    db.refresh(consent)
    return consent


def submit(db: Session, user: User, request: ContributionRequest) -> CommunityContribution:
    repository.lock_community_writes(db)
    consent = repository.get_consent(db, user.id)
    if not request.copyright_confirmed:
        raise BadRequest("Copyright confirmation is required for community contributions")
    if request.consent_to_training and (
        consent is None or not consent.consent_enabled or consent.disclosure_version != CONSENT_VERSION
    ):
        raise BadRequest("Enable training permission in Settings before consenting to training")
    if contains_identifiers(request.title, request.body, request.source or ""):
        raise ValidationFailure("Remove personal identifiers before submitting this contribution.")
    item = repository.add_contribution(
        db,
        user_id=user.id,
        title=request.title.strip(),
        body=request.body.strip(),
        category=request.category.strip().lower(),
        source=request.source.strip() if request.source else None,
        consent_to_training=request.consent_to_training,
        copyright_confirmed=request.copyright_confirmed,
        deidentified=False,
        review_status="pending",
    )
    db.commit()
    db.refresh(item)
    return item


def list_mine(db: Session, user_id: int) -> list[dict]:
    return [
        {
            "id": item.id,
            "title": item.title,
            "category": item.category,
            "review_status": item.review_status,
            "quality_rating": item.quality_rating,
            "consent_to_training": item.consent_to_training,
            "submitted_at": item.submitted_at.isoformat(),
        }
        for item in repository.list_user_contributions(db, user_id)
    ]


def set_contribution_consent(db: Session, user_id: int, contribution_id: int, enabled: bool) -> dict:
    repository.lock_community_writes(db)
    item = repository.get_user_contribution(db, user_id, contribution_id)
    if not item:
        raise NotFoundError("Contribution not found.")
    if enabled:
        if not repository.has_current_consent(db, user_id) or not item.copyright_confirmed:
            raise BadRequest("Enable training permission in Settings and confirm ownership first.")
    else:
        invalidate_datasets(db, [item.id])
    item.consent_to_training = enabled
    db.commit()
    return {"id": item.id, "consent_to_training": item.consent_to_training}


def list_for_review(db: Session) -> list[dict]:
    return [
        {
            "id": item.id,
            "title": item.title,
            "body": item.body,
            "category": item.category,
            "source": item.source,
            "review_status": item.review_status,
            "quality_rating": item.quality_rating,
            "consent_to_training": item.consent_to_training,
            "deidentified": item.deidentified,
            "copyright_confirmed": item.copyright_confirmed,
            "submitted_at": item.submitted_at.isoformat(),
        }
        for item in repository.list_all_contributions(db)
    ]


def review(db: Session, reviewer: User, contribution_id: int, request: ContributionReviewRequest) -> dict:
    repository.lock_community_writes(db)
    item = repository.get_contribution(db, contribution_id)
    if not item:
        raise NotFoundError("Contribution not found")
    existing = repository.get_approved(db, item.id)
    if request.status == "approved":
        if not request.deidentified:
            raise BadRequest("Approved contributions must be confirmed as de-identified")
        if not item.copyright_confirmed:
            raise BadRequest("Approved contributions require copyright confirmation")
        quality = request.quality_rating
        if quality is None or quality < MINIMUM_APPROVAL_RATING:
            raise BadRequest("Approved contributions require a quality rating of at least 3")
        public_title = request.public_title or item.title
        public_body = request.public_body or item.body
        public_source = request.public_source if request.public_source is not None else item.source
        if contains_identifiers(public_title, public_body, public_source or ""):
            raise ValidationFailure("Remove personal identifiers from the public copy before approval.")
        embedding = json.dumps(hashed_embedding(public_title + " " + public_body))
        if existing:
            existing.title = public_title
            existing.body = public_body
            existing.category = item.category
            existing.source_reference = public_source
            existing.quality_score = quality
            existing.embedding_json = embedding
        else:
            repository.add_approved(
                db, source_contribution_id=item.id, title=public_title, body=public_body, category=item.category,
                source_reference=public_source, quality_score=quality, embedding_json=embedding,
            )
    elif existing:
        db.delete(existing)
    # Any change to a reviewed contribution invalidates drafts that snapshotted it.
    invalidate_datasets(db, [item.id])
    item.review_status = request.status
    item.deidentified = request.deidentified
    item.quality_rating = request.quality_rating
    repository.add_review(db, item.id, reviewer.id, request.status, request.quality_rating, request.notes)
    db.commit()
    return {"id": item.id, "review_status": item.review_status, "quality_rating": item.quality_rating}


def history(db: Session, contribution_id: int):
    return repository.list_reviews(db, contribution_id)
