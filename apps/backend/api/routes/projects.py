from fastapi import APIRouter

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.projects import ProjectRequest, ProjectUpdateRequest
from apps.backend.services.projects import generation

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("")
def create_project(request: ProjectRequest, user: CurrentUser, db: DbSession):
    return generation.create_project(db, user, request)


@router.get("")
def list_projects(user: CurrentUser, db: DbSession):
    return generation.list_projects(db, user.id)


@router.patch("/{project_id}")
def update_project(project_id: int, request: ProjectUpdateRequest, user: CurrentUser, db: DbSession):
    return generation.update_project(db, user.id, project_id, request)


@router.delete("/{project_id}")
def delete_project(project_id: int, user: CurrentUser, db: DbSession):
    generation.delete_project(db, user.id, project_id)
    return {"deleted": True}
