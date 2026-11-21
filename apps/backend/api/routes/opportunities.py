from fastapi import APIRouter, Query

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.opportunities import OpportunitySaveRequest, OpportunityStatusRequest
from apps.backend.services.opportunities import directories

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("")
def opportunities(q: str = Query(default="", max_length=160)):
    return directories.official_directories(q)


@router.post("/save")
def save_opportunity(request: OpportunitySaveRequest, user: CurrentUser, db: DbSession):
    return directories.save(db, user.id, request)


@router.get("/saved")
def list_saved_opportunities(user: CurrentUser, db: DbSession):
    return directories.list_saved(db, user.id)


@router.delete("/saved/{opportunity_id}")
def remove_saved_opportunity(opportunity_id: int, user: CurrentUser, db: DbSession):
    directories.remove(db, user.id, opportunity_id)
    return {"deleted": True}


@router.patch("/saved/{opportunity_id}")
def update_opportunity(opportunity_id: int, request: OpportunityStatusRequest, user: CurrentUser, db: DbSession):
    return directories.update_status(db, user.id, opportunity_id, request.application_status)
