from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from apps.backend.models import AlternateTitle, CustomOccupation, Descriptor, Occupation, RelatedOccupation, SavedCareer
from packages.onet.constants import RATED_SKILL_CATEGORIES


def _like_pattern(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def search(db: Session, text: str, limit: int) -> list[Occupation]:
    match = _like_pattern(text)
    return (
        db.query(Occupation)
        .join(AlternateTitle, isouter=True)
        .filter(
            Occupation.dataset_version.is_not(None),
            or_(
                Occupation.title.ilike(match, escape="\\"),
                Occupation.description.ilike(match, escape="\\"),
                Occupation.onet_soc_code.ilike(match, escape="\\"),
                AlternateTitle.title.ilike(match, escape="\\"),
            ),
        )
        .distinct()
        .order_by(Occupation.title, Occupation.id)
        .limit(limit)
        .all()
    )


def get_active(db: Session, occupation_id: int) -> Occupation | None:
    """An occupation that is part of the currently imported release."""
    occupation = db.get(Occupation, occupation_id)
    return occupation if occupation and occupation.dataset_version else None


def find_by_title_or_code(db: Session, text: str) -> Occupation | None:
    return (
        db.query(Occupation)
        .filter(
            Occupation.dataset_version.is_not(None),
            or_(
                Occupation.title.ilike(text.replace("%", r"\%").replace("_", r"\_"), escape="\\"),
                Occupation.onet_soc_code == text,
            ),
        )
        .first()
    )


def descriptor_categories(db: Session, occupation_id: int) -> list[str]:
    rows = (
        db.query(Descriptor.category).filter_by(occupation_id=occupation_id)
        .distinct().order_by(Descriptor.category)
    )
    return [row[0] for row in rows]


def descriptor_count(db: Session, occupation_id: int, category: str | None) -> int:
    query = db.query(Descriptor).filter_by(occupation_id=occupation_id)
    if category:
        query = query.filter_by(category=category)
    return query.count()


def descriptors(db: Session, occupation_id: int, category: str | None, offset: int, limit: int) -> list[Descriptor]:
    query = db.query(Descriptor).filter_by(occupation_id=occupation_id)
    if category:
        query = query.filter_by(category=category)
    return query.order_by(Descriptor.category, Descriptor.name, Descriptor.id).offset(offset).limit(limit).all()


def alternate_titles(db: Session, occupation_id: int) -> list[AlternateTitle]:
    return db.query(AlternateTitle).filter_by(occupation_id=occupation_id).all()


def related_occupations(db: Session, occupation_id: int) -> list[RelatedOccupation]:
    return db.query(RelatedOccupation).filter_by(occupation_id=occupation_id).all()


def top_importance_descriptors(db: Session, occupation_id: int, limit: int = 50) -> list[Descriptor]:
    return (
        db.query(Descriptor)
        .filter(
            Descriptor.occupation_id == occupation_id,
            Descriptor.category.in_(RATED_SKILL_CATEGORIES), Descriptor.scale == "IM",
            Descriptor.rating.is_not(None),
        )
        .order_by(Descriptor.rating.desc(), Descriptor.name).limit(limit).all()
    )


def skill_descriptors(db: Session, occupation_id: int) -> list[Descriptor]:
    return (
        db.query(Descriptor)
        .filter(Descriptor.occupation_id == occupation_id, Descriptor.category.in_(RATED_SKILL_CATEGORIES))
        .order_by(Descriptor.category, Descriptor.name, Descriptor.id)
        .all()
    )


def saved_careers(db: Session, user_id: int) -> list[Occupation]:
    return list(db.scalars(
        select(Occupation).join(SavedCareer).where(SavedCareer.user_id == user_id).order_by(Occupation.title)
    ))


def get_saved_career(db: Session, user_id: int, occupation_id: int) -> SavedCareer | None:
    return db.get(SavedCareer, (user_id, occupation_id))


def add_saved_career(db: Session, user_id: int, occupation_id: int) -> None:
    db.add(SavedCareer(user_id=user_id, occupation_id=occupation_id))


def remove_saved_career(db: Session, user_id: int, occupation_id: int) -> None:
    db.execute(delete(SavedCareer).where(SavedCareer.user_id == user_id, SavedCareer.occupation_id == occupation_id))


def add_custom_occupation(db: Session, user_id: int, title: str, industry: str | None,
                          description: str | None) -> CustomOccupation:
    item = CustomOccupation(user_id=user_id, title=title, industry=industry, description=description)
    db.add(item)
    return item


def list_custom_occupations(db: Session, user_id: int) -> list[CustomOccupation]:
    return db.query(CustomOccupation).filter_by(user_id=user_id).order_by(CustomOccupation.created_at.desc()).all()


def get_custom_occupation(db: Session, user_id: int, occupation_id: int) -> CustomOccupation | None:
    return db.query(CustomOccupation).filter_by(id=occupation_id, user_id=user_id).first()


def find_custom_occupation(db: Session, user_id: int, title: str) -> CustomOccupation | None:
    return db.query(CustomOccupation).filter_by(user_id=user_id, title=title).first()
