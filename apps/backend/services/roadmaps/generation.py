"""Generate, store, and manage learning roadmaps and their activities."""
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import NotFoundError
from apps.backend.models import User
from apps.backend.repositories import roadmaps as repository
from apps.backend.schemas.roadmaps import LearningActivityRequest, RoadmapRequest
from apps.backend.services.ai.grounded import generate_grounded


def create_roadmap(db: Session, user: User, request: RoadmapRequest) -> dict:
    def prompt(sources: str) -> str:
        return (
            f"Create an adaptive learning roadmap for {request.occupation_title}. "
            f"User interests: {request.interests or 'Not provided'}. "
            f"Current skills: {request.current_skills}. "
            "Include prerequisites, measurable objectives, time ranges, practice projects, and completion criteria. "
            "Consider college, vocational, apprenticeship and work-based paths where appropriate.\n"
            f"{sources}"
        )

    content, records = generate_grounded(db, user, "roadmap", request.occupation_title, prompt)
    roadmap = repository.add_roadmap(db, user.id, request.occupation_title.strip(), content, records)
    db.commit()
    db.refresh(roadmap)
    return {"id": roadmap.id, "occupation_title": roadmap.occupation_title, "content": content, "sources": records}


def list_roadmaps(db: Session, user_id: int) -> list[dict]:
    return [
        {
            "id": item.id,
            "occupation_title": item.occupation_title,
            "content": item.content,
            "sources": item.sources,
            "created_at": item.created_at.isoformat(),
        }
        for item in repository.list_roadmaps(db, user_id)
    ]


def delete_roadmap(db: Session, user_id: int, roadmap_id: int) -> None:
    roadmap = repository.get_roadmap(db, user_id, roadmap_id)
    if not roadmap:
        raise NotFoundError("Roadmap not found")
    repository.delete_roadmap(db, roadmap)
    db.commit()


def _require_roadmap(db: Session, user_id: int, roadmap_id: int | None) -> None:
    if roadmap_id and not repository.get_roadmap(db, user_id, roadmap_id):
        raise NotFoundError("Roadmap not found")


def create_activity(db: Session, user_id: int, request: LearningActivityRequest):
    _require_roadmap(db, user_id, request.roadmap_id)
    item = repository.add_activity(db, user_id, request.roadmap_id, request.title, request.status, request.notes)
    db.commit()
    db.refresh(item)
    return item


def list_activities(db: Session, user_id: int):
    return repository.list_activities(db, user_id)


def update_activity(db: Session, user_id: int, activity_id: int, request: LearningActivityRequest):
    item = repository.get_activity(db, user_id, activity_id)
    if not item:
        raise NotFoundError("Learning activity not found")
    if "roadmap_id" in request.model_fields_set:
        _require_roadmap(db, user_id, request.roadmap_id)
        item.roadmap_id = request.roadmap_id
    item.title = request.title
    item.status = request.status
    item.notes = request.notes
    db.commit()
    db.refresh(item)
    return item
