from sqlalchemy.orm import Session

from apps.backend.models import Project


def add_project(db: Session, user_id: int, title: str, description: str, status: str = "planned") -> Project:
    project = Project(user_id=user_id, title=title, description=description, status=status)
    db.add(project)
    return project


def list_projects(db: Session, user_id: int) -> list[Project]:
    return db.query(Project).filter_by(user_id=user_id).order_by(Project.created_at.desc()).all()


def get_project(db: Session, user_id: int, project_id: int) -> Project | None:
    return db.query(Project).filter_by(id=project_id, user_id=user_id).first()
