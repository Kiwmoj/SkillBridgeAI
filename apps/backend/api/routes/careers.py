from fastapi import APIRouter, Query

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.careers import CareerCompareRequest, CustomOccupationRequest
from apps.backend.services.careers import explorer

router = APIRouter(tags=["careers"])


@router.get("/occupations/search")
def search_occupations(
    db: DbSession,
    q: str = Query(default="", max_length=255),
    limit: int = Query(default=30, ge=1, le=100),
):
    return explorer.search(db, q, limit)


@router.get("/occupations/saved")
def saved_careers(user: CurrentUser, db: DbSession):
    return explorer.saved_careers(db, user.id)


@router.put("/occupations/saved/{occupation_id}")
def save_career(occupation_id: int, user: CurrentUser, db: DbSession):
    explorer.save_career(db, user.id, occupation_id)
    return {"saved": True}


@router.delete("/occupations/saved/{occupation_id}")
def remove_saved_career(occupation_id: int, user: CurrentUser, db: DbSession):
    explorer.remove_saved_career(db, user.id, occupation_id)
    return {"saved": False}


@router.get("/occupations/{occupation_id}")
def occupation_detail(
    occupation_id: int,
    db: DbSession,
    category: str | None = Query(default=None, max_length=64),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=300, ge=1, le=500),
):
    return explorer.detail(db, occupation_id, category, offset, limit)


@router.post("/occupations/compare")
def compare_careers(request: CareerCompareRequest, db: DbSession):
    return explorer.compare(db, request.occupation_ids)


@router.post("/custom-occupations")
def create_custom_occupation(request: CustomOccupationRequest, user: CurrentUser, db: DbSession):
    return explorer.create_custom_occupation(db, user.id, request.title, request.industry, request.description)


@router.get("/custom-occupations")
def list_custom_occupations(user: CurrentUser, db: DbSession):
    return explorer.list_custom_occupations(db, user.id)


@router.delete("/custom-occupations/{occupation_id}")
def delete_custom_occupation(occupation_id: int, user: CurrentUser, db: DbSession):
    explorer.delete_custom_occupation(db, user.id, occupation_id)
    return {"deleted": True}
