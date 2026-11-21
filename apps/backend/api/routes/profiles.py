from fastapi import APIRouter

from pydantic import BaseModel

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.profiles import ProfileRequest
from apps.backend.services import levels
from apps.backend.services.authentication import profiles

router = APIRouter(prefix="/profile", tags=["profiles"])


class LevelRequest(BaseModel):
    skill_level: str


@router.get("/level")
def get_level(user: CurrentUser, db: DbSession):
    return levels.describe(db, user.id)


@router.put("/level")
def set_level(request: LevelRequest, user: CurrentUser, db: DbSession):
    levels.set_level(db, user.id, request.skill_level)
    return levels.describe(db, user.id)


@router.get("")
def get_profile(user: CurrentUser, db: DbSession):
    return profiles.get_profile(db, user)


@router.put("")
def update_profile(request: ProfileRequest, user: CurrentUser, db: DbSession):
    return profiles.update_profile(db, user, request)
