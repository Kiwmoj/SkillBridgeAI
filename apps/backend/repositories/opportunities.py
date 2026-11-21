from sqlalchemy.orm import Session

from apps.backend.models import Opportunity


def add_saved(db: Session, user_id: int, title: str, organization: str | None, url: str | None,
              details: str | None) -> Opportunity:
    item = Opportunity(user_id=user_id, title=title, organization=organization, url=url, details=details, saved=True)
    db.add(item)
    return item


def list_saved(db: Session, user_id: int) -> list[Opportunity]:
    return db.query(Opportunity).filter_by(user_id=user_id, saved=True).order_by(Opportunity.id.desc()).all()


def count_saved(db: Session, user_id: int) -> int:
    return db.query(Opportunity).filter_by(user_id=user_id, saved=True).count()


def get_saved(db: Session, user_id: int, opportunity_id: int) -> Opportunity | None:
    return db.query(Opportunity).filter_by(id=opportunity_id, user_id=user_id).first()
