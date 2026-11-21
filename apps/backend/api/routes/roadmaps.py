from fastapi import APIRouter

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.roadmaps import LearningActivityRequest, RoadmapRequest
from apps.backend.services.roadmaps import generation

router = APIRouter(tags=["roadmaps"])


@router.post("/roadmaps")
def create_roadmap(request: RoadmapRequest, user: CurrentUser, db: DbSession):
    return generation.create_roadmap(db, user, request)


@router.get("/roadmaps")
def list_roadmaps(user: CurrentUser, db: DbSession):
    return generation.list_roadmaps(db, user.id)


@router.delete("/roadmaps/{roadmap_id}")
def delete_roadmap(roadmap_id: int, user: CurrentUser, db: DbSession):
    generation.delete_roadmap(db, user.id, roadmap_id)
    return {"deleted": True}


@router.post("/activities")
def create_activity(request: LearningActivityRequest, user: CurrentUser, db: DbSession):
    return generation.create_activity(db, user.id, request)


@router.get("/activities")
def list_activities(user: CurrentUser, db: DbSession):
    return generation.list_activities(db, user.id)


@router.patch("/activities/{activity_id}")
def update_activity(activity_id: int, request: LearningActivityRequest, user: CurrentUser, db: DbSession):
    return generation.update_activity(db, user.id, activity_id, request)
