from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import Portfolio


def add_item(db: Session, user_id: int, filename: str, stored_path: str, mime_type: str) -> Portfolio:
    item = Portfolio(user_id=user_id, filename=filename, stored_path=stored_path, mime_type=mime_type)
    db.add(item)
    return item


def list_items(db: Session, user_id: int) -> list[Portfolio]:
    return db.query(Portfolio).filter_by(user_id=user_id).order_by(Portfolio.created_at.desc()).all()


def get_item(db: Session, user_id: int, portfolio_id: int) -> Portfolio | None:
    return db.query(Portfolio).filter_by(id=portfolio_id, user_id=user_id).first()


def count_items(db: Session, user_id: int) -> int:
    return db.query(Portfolio).filter_by(user_id=user_id).count()


def stored_paths(db: Session, user_id: int) -> list[str]:
    return list(db.scalars(select(Portfolio.stored_path).where(Portfolio.user_id == user_id)))
