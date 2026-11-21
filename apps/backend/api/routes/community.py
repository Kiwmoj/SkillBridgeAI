from fastapi import APIRouter

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.community import ContributionRequest, ContributionResponse, TrainingConsentRequest
from apps.backend.services.community import contributions

router = APIRouter(tags=["community"])


@router.get("/training-consent")
def get_training_consent(user: CurrentUser, db: DbSession):
    return contributions.consent_summary(db, user.id)


@router.put("/training-consent")
def update_training_consent(request: TrainingConsentRequest, user: CurrentUser, db: DbSession):
    return contributions.update_consent(db, user.id, request)


@router.post("/contributions", response_model=ContributionResponse)
def submit_contribution(request: ContributionRequest, user: CurrentUser, db: DbSession):
    item = contributions.submit(db, user, request)
    return ContributionResponse(
        id=item.id, title=item.title, category=item.category, review_status=item.review_status,
        consent_to_training=item.consent_to_training, quality_rating=item.quality_rating,
    )


@router.get("/contributions")
def my_contributions(user: CurrentUser, db: DbSession):
    return contributions.list_mine(db, user.id)


@router.put("/contributions/{contribution_id}/consent")
def set_contribution_consent(contribution_id: int, request: TrainingConsentRequest, user: CurrentUser, db: DbSession):
    return contributions.set_contribution_consent(db, user.id, contribution_id, request.consent_enabled)
