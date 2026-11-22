from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.orm import Session

from apps.backend.models import AlternateTitle, CustomOccupation, Descriptor, Occupation, RelatedOccupation, SavedCareer
from packages.onet.constants import RATED_SKILL_CATEGORIES


def _like_pattern(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _search_stem(text: str) -> str:
    """Trim common word endings so 'nursing' also finds 'Nurses'."""
    word = text.strip()
    for suffix in ("ing", "ers", "er", "es", "s"):
        if len(word) - len(suffix) >= 4 and word.lower().endswith(suffix):
            return word[: -len(suffix)]
    return word


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _ranked_ids(db: Session, text: str, filters, limit: int) -> list[int]:
    """Occupation IDs best first: exact title, then title/alternate-title word matches, then looser matches.

    Ties prefer the base occupation (.00 code) and then the shorter, more general title.
    """
    phrase = text.strip().lower()
    stem = _escape(_search_stem(text).lower())
    title, alt = func.lower(Occupation.title), func.lower(AlternateTitle.title)
    rank = case(
        (title == phrase, 0),
        (alt == phrase, 0),
        (title.like(f"{stem}%", escape="\\"), 1),
        (title.like(f"% {stem}%", escape="\\"), 1),
        (alt.like(f"{stem}%", escape="\\"), 2),
        (alt.like(f"% {stem}%", escape="\\"), 2),
        (title.like(f"%{stem}%", escape="\\"), 3),
        (alt.like(f"%{stem}%", escape="\\"), 4),
        (Occupation.onet_soc_code.like(f"%{stem}%", escape="\\"), 4),
        else_=5,
    )
    base_code = case((Occupation.onet_soc_code.like("%.00"), 0), else_=1)
    rows = (
        db.query(Occupation.id)
        .join(AlternateTitle, isouter=True)
        .filter(Occupation.dataset_version.is_not(None), filters)
        .group_by(Occupation.id, Occupation.title)
        .order_by(func.min(rank), func.min(base_code), func.length(Occupation.title), Occupation.title, Occupation.id)
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


def search(db: Session, text: str, limit: int) -> list[Occupation]:
    stem = _escape(_search_stem(text).lower())
    match = f"%{stem}%"
    phrase_filter = or_(
        func.lower(Occupation.title).like(match, escape="\\"),
        func.lower(Occupation.description).like(match, escape="\\"),
        func.lower(Occupation.onet_soc_code).like(match, escape="\\"),
        func.lower(AlternateTitle.title).like(match, escape="\\"),
    )
    order = _ranked_ids(db, text, phrase_filter, limit)
    if not order:
        # "computer science teacher": every word must appear somewhere, in any order.
        words = [_escape(_search_stem(word).lower()) for word in text.split() if len(word) >= 3]
        if len(words) > 1:
            word_filters = [
                or_(
                    func.lower(Occupation.title).like(f"%{word}%", escape="\\"),
                    func.lower(AlternateTitle.title).like(f"%{word}%", escape="\\"),
                    func.lower(Occupation.description).like(f"%{word}%", escape="\\"),
                )
                for word in words
            ]
            order = _ranked_ids(db, text, and_(*word_filters), limit)
    if not order:
        return []
    found = {item.id: item for item in db.query(Occupation).filter(Occupation.id.in_(order)).all()}
    return [found[i] for i in order]


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


def work_style_descriptors(db: Session, occupation_id: int) -> list[Descriptor]:
    """Work styles (for example Leadership or Cooperation) rated on the importance scale."""
    return (
        db.query(Descriptor)
        .filter(Descriptor.occupation_id == occupation_id, Descriptor.category == "Work Styles",
                Descriptor.scale == "WI")
        .order_by(Descriptor.name, Descriptor.id)
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
