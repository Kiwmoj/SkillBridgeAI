from sqlalchemy.orm import Session

from apps.backend.models import AIUsage, LearningActivity, Project, SkillAssessment


def record_ai_usage(db: Session, user_id: int, provider: str, feature: str, success: bool, latency_ms: int) -> None:
    db.add(AIUsage(user_id=user_id, provider=provider, feature=feature, success=success, latency_ms=latency_ms))
    db.commit()


def list_projects(db: Session, user_id: int) -> list[Project]:
    return db.query(Project).filter_by(user_id=user_id).all()


def list_activities(db: Session, user_id: int) -> list[LearningActivity]:
    return db.query(LearningActivity).filter_by(user_id=user_id).all()


def count_assessments(db: Session, user_id: int) -> int:
    return db.query(SkillAssessment).filter_by(user_id=user_id).count()


def usage_totals(db: Session) -> tuple[int, int]:
    usage = db.query(AIUsage).all()
    return len(usage), sum(item.success for item in usage)
