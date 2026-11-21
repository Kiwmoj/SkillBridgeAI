"""Learning Center: in-platform lessons built from official O*NET Content Model definitions.

A lesson combines the element's official definition, the occupations that rate it most important,
and real O*NET task statements from those occupations as practice scenarios. External courses are
offered as clearly labelled links, or embeds only where the provider permits framing and reuse.
"""
from urllib.parse import quote

from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import NotFoundError, ValidationFailure
from apps.backend.database.base import utcnow
from apps.backend.models import Descriptor, LessonProgress, Occupation, OnetElement
from apps.backend.services.careers.explorer import is_reported

LESSON_CATEGORIES = ("Essential Skills", "Skills", "Transferable Skills", "Knowledge", "Abilities", "Work Activities")
LESSON_STATUSES = ("not_started", "in_progress", "completed")
REFLECTION_PROMPTS = (
    "Describe a recent situation where you used {name}. What went well, and what would you change?",
    "Which of the practice scenarios below feels hardest for you right now, and why?",
    "Set one concrete goal for practising {name} this week and how you will know you met it.",
)


def lesson_index(db: Session) -> dict[str, str]:
    """element_id -> the lesson category it is rated under (first match in LESSON_CATEGORIES order)."""
    pairs = db.query(Descriptor.element_id, Descriptor.category).filter(
        Descriptor.category.in_(LESSON_CATEGORIES), Descriptor.scale == "IM", Descriptor.element_id != "",
    ).distinct().all()
    ranked: dict[str, str] = {}
    for element_id, category in sorted(pairs, key=lambda pair: LESSON_CATEGORIES.index(pair[1])):
        ranked.setdefault(element_id, category)
    return ranked


def list_lessons(db: Session, user_id: int, category: str | None = None, query: str | None = None) -> list[dict]:
    index = lesson_index(db)
    if category:
        index = {k: v for k, v in index.items() if v == category}
    elements = db.query(OnetElement).filter(OnetElement.element_id.in_(index.keys())).all() if index else []
    if query:
        needle = query.casefold().strip()
        elements = [e for e in elements if needle in e.name.casefold() or needle in (e.description or "").casefold()]
    progress = {p.element_id: p.status for p in db.query(LessonProgress).filter_by(user_id=user_id)}
    lessons = [{
        "element_id": e.element_id, "name": e.name, "category": index[e.element_id],
        "summary": e.description, "status": progress.get(e.element_id, "not_started"),
    } for e in elements]
    return sorted(lessons, key=lambda item: (LESSON_CATEGORIES.index(item["category"]), item["name"]))


def _hierarchy(db: Session, element_id: str) -> list[dict]:
    parts = element_id.split(".")
    parents = [".".join(parts[:i]) for i in range(1, len(parts))]
    found = {e.element_id: e.name for e in db.query(OnetElement).filter(OnetElement.element_id.in_(parents))}
    return [{"element_id": p, "name": found[p]} for p in parents if p in found]


def _top_occupations(db: Session, element_id: str, limit: int = 8) -> list[dict]:
    rows = (
        db.query(Descriptor, Occupation)
        .join(Occupation, Occupation.id == Descriptor.occupation_id)
        .filter(Descriptor.element_id == element_id, Descriptor.scale == "IM", Descriptor.rating.is_not(None),
                Occupation.dataset_version.is_not(None))
        .order_by(Descriptor.rating.desc())
        .limit(limit * 5).all()
    )
    occupations, seen = [], set()
    for descriptor, occupation in rows:
        if occupation.id in seen or not is_reported(descriptor):
            continue
        seen.add(occupation.id)
        occupations.append({"id": occupation.id, "title": occupation.title, "onet_soc_code": occupation.onet_soc_code,
                            "importance": descriptor.rating})
        if len(occupations) == limit:
            break
    return occupations


def _practice_scenarios(db: Session, occupations: list[dict]) -> list[dict]:
    if not occupations:
        return []
    tasks = (db.query(Descriptor.name, Occupation.title)
             .join(Occupation, Occupation.id == Descriptor.occupation_id)
             .filter(Descriptor.category == "Tasks", Descriptor.occupation_id.in_([o["id"] for o in occupations[:4]]))
             .order_by(Descriptor.id).all())
    scenarios, per_occupation = [], {}
    for task, title in tasks:
        if per_occupation.get(title, 0) < 2:
            per_occupation[title] = per_occupation.get(title, 0) + 1
            scenarios.append({"task": task, "occupation": title})
    return scenarios[:8]


def lesson_detail(db: Session, user_id: int, element_id: str) -> dict:
    index = lesson_index(db)
    element = db.get(OnetElement, element_id)
    if element is None or element_id not in index:
        raise NotFoundError("Lesson not found")
    occupations = _top_occupations(db, element_id)
    progress = db.query(LessonProgress).filter_by(user_id=user_id, element_id=element_id).first()
    encoded = quote(element.name)
    onet_url = f"https://www.onetonline.org/find/descriptor/result/{element.element_id}"
    return {
        "element_id": element.element_id,
        "name": element.name,
        "category": index[element_id],
        "definition": element.description,
        "hierarchy": _hierarchy(db, element_id),
        "top_occupations": occupations,
        "practice_scenarios": _practice_scenarios(db, occupations),
        "reflection_prompts": [prompt.format(name=element.name) for prompt in REFLECTION_PROMPTS],
        "progress": {"status": progress.status if progress else "not_started",
                     "notes": progress.notes if progress else None},
        "source": {"credit": "O*NET® Content Model and Database, U.S. Department of Labor/ETA (CC BY 4.0)",
                   "url": onet_url},
        "resources": [
            {"title": f"O*NET OnLine: occupations that use {element.name}", "provider": "O*NET OnLine (USDOL/ETA)",
             "url": onet_url, "embeddable": True, "license": "CC BY 4.0",
             "summary": "The official O*NET page listing occupations where this element matters most."},
            {"title": f"MIT OpenCourseWare search: {element.name}", "provider": "MIT OpenCourseWare",
             "url": f"https://ocw.mit.edu/search/?q={encoded}", "embeddable": True, "license": "CC BY-NC-SA 4.0",
             "summary": "Free MIT course materials (lecture notes, assignments, videos) related to this topic."},
            {"title": f"Khan Academy search: {element.name}", "provider": "Khan Academy",
             "url": f"https://www.khanacademy.org/search?page_search_query={encoded}", "embeddable": False,
             "license": "See provider terms",
             "summary": "Free practice lessons and videos. Opens on Khan Academy; not hosted by SkillBridge."},
        ],
    }


def update_progress(db: Session, user_id: int, element_id: str, status: str, notes: str | None) -> dict:
    if status not in LESSON_STATUSES:
        raise ValidationFailure("Status must be not_started, in_progress, or completed.")
    if db.get(OnetElement, element_id) is None:
        raise NotFoundError("Lesson not found")
    progress = db.query(LessonProgress).filter_by(user_id=user_id, element_id=element_id).first()
    if progress is None:
        progress = LessonProgress(user_id=user_id, element_id=element_id)
        db.add(progress)
    progress.status = status
    progress.notes = notes
    progress.updated_at = utcnow()
    db.commit()
    return {"element_id": element_id, "status": progress.status, "notes": progress.notes}


def progress_counts(db: Session, user_id: int) -> dict[str, int]:
    counts = {"in_progress": 0, "completed": 0}
    for status, total in (db.query(LessonProgress.status, func.count()).filter_by(user_id=user_id)
                          .group_by(LessonProgress.status).all()):
        counts[status] = total
    return {"lessons_in_progress": counts["in_progress"], "lessons_completed": counts["completed"]}
