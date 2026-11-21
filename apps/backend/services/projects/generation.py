"""Generate and track portfolio projects."""
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import BadRequest, NotFoundError
from apps.backend.models import User
from apps.backend.repositories import projects as repository
from apps.backend.schemas.projects import ProjectRequest
from apps.backend.services.ai.grounded import generate_grounded

PROJECT_STATUSES = {"planned", "in_progress", "completed"}


def create_project(db: Session, user: User, request: ProjectRequest) -> dict:
    occupation = request.occupation.strip()
    title = request.title.strip() if request.title else f"{occupation} portfolio project"

    def prompt(sources: str) -> str:
        return (
            f"Generate a realistic, ethical project for a student pursuing {occupation}. "
            f"Project theme: {title}. Student-provided experience and skills: {request.experience or 'Not provided'}. "
            "Include difficulty, materials, objectives, phases, outcomes and portfolio presentation. "
            "Label this as AI-generated guidance.\n"
            f"{sources}"
        )

    description, records = generate_grounded(db, user, "project_generator", request.occupation, prompt)
    project = repository.add_project(db, user.id, title[:255], description)
    db.commit()
    db.refresh(project)
    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "status": project.status,
        "sources": records,
    }


def list_projects(db: Session, user_id: int):
    return repository.list_projects(db, user_id)


def update_status(db: Session, user_id: int, project_id: int, status: str):
    if status not in PROJECT_STATUSES:
        raise BadRequest("Invalid project status")
    project = repository.get_project(db, user_id, project_id)
    if not project:
        raise NotFoundError("Project not found")
    project.status = status
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, user_id: int, project_id: int) -> None:
    project = repository.get_project(db, user_id, project_id)
    if not project:
        raise NotFoundError("Project not found")
    db.delete(project)
    db.commit()
