from fastapi import APIRouter

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.services.analytics import progress

router = APIRouter(tags=["analytics"])


@router.get("/progress")
def progress_summary(user: CurrentUser, db: DbSession):
    return progress.summary(db, user.id)
