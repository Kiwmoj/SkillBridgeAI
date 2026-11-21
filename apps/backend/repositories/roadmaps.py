from sqlalchemy import update
from sqlalchemy.orm import Session

from apps.backend.models import LearningActivity, Roadmap


def add_roadmap(db: Session, user_id: int, occupation_title: str, content: str, sources: list[dict]) -> Roadmap:
    roadmap = Roadmap(user_id=user_id, occupation_title=occupation_title, content=content, sources=sources)
    db.add(roadmap)
    return roadmap


def list_roadmaps(db: Session, user_id: int) -> list[Roadmap]:
    return db.query(Roadmap).filter_by(user_id=user_id).order_by(Roadmap.created_at.desc()).all()


def get_roadmap(db: Session, user_id: int, roadmap_id: int) -> Roadmap | None:
    return db.query(Roadmap).filter_by(id=roadmap_id, user_id=user_id).first()


def count_roadmaps(db: Session, user_id: int) -> int:
    return db.query(Roadmap).filter_by(user_id=user_id).count()


def delete_roadmap(db: Session, roadmap: Roadmap) -> None:
    """Detach the owner's activities from the roadmap before removing it."""
    db.execute(update(LearningActivity).where(
        LearningActivity.roadmap_id == roadmap.id, LearningActivity.user_id == roadmap.user_id,
    ).values(roadmap_id=None))
    db.delete(roadmap)


def add_activity(db: Session, user_id: int, roadmap_id: int | None, title: str, status: str,
                 notes: str | None) -> LearningActivity:
    item = LearningActivity(user_id=user_id, roadmap_id=roadmap_id, title=title, status=status, notes=notes)
    db.add(item)
    return item


def list_activities(db: Session, user_id: int) -> list[LearningActivity]:
    return db.query(LearningActivity).filter_by(user_id=user_id).order_by(LearningActivity.created_at.desc()).all()


def get_activity(db: Session, user_id: int, activity_id: int) -> LearningActivity | None:
    return db.query(LearningActivity).filter_by(id=activity_id, user_id=user_id).first()
