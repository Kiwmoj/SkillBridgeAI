from fastapi import APIRouter

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.profiles import ProfileRequest
from apps.backend.services.authentication import profiles

router = APIRouter(prefix="/profile", tags=["profiles"])


@router.get("")
def get_profile(user: CurrentUser, db: DbSession):
    return profiles.get_profile(db, user)


@router.put("")
def update_profile(request: ProfileRequest, user: CurrentUser, db: DbSession):
    return profiles.update_profile(db, user, request)
