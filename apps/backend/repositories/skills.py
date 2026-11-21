from sqlalchemy.orm import Session

from apps.backend.models import SkillAssessment


def add_assessment(db: Session, user_id: int, occupation_title: str, skill_name: str, rating: float) -> SkillAssessment:
    item = SkillAssessment(user_id=user_id, occupation_title=occupation_title, skill_name=skill_name, rating=rating)
    db.add(item)
    return item


def list_assessments(db: Session, user_id: int) -> list[SkillAssessment]:
    return db.query(SkillAssessment).filter_by(user_id=user_id).order_by(SkillAssessment.created_at.desc()).all()
