"""Compare self-reported skills with imported O*NET descriptors for an occupation."""
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import NotFoundError
from apps.backend.models import Descriptor
from apps.backend.repositories import occupations as occupations_repository
from apps.backend.repositories import skills as repository
from apps.backend.schemas.skills import SkillAssessmentRequest, SkillGapRequest
from apps.backend.services.careers.explorer import is_reported
from apps.backend.services.levels import LEVELS, effective_level
from apps.backend.services.skills.matching import match_descriptors, match_tools

UNVERIFIED_NOTICE = (
    "We could not find this occupation in the imported official O*NET data. "
    "Try a more common job title, for example 'Registered Nurses' or 'Software Developers'."
)
MATCH_NOTICE = (
    "Matches are self-reported. A gap means a skill was not listed, not that it was tested. "
    "Everyday wording such as 'communication' is matched to the related O*NET skills."
)


def _descriptors(db: Session, occupation_id: int) -> dict[str, Descriptor]:
    """One reported descriptor per name across skills, knowledge, abilities and work styles."""
    unique: dict[str, Descriptor] = {}
    rows = list(occupations_repository.skill_descriptors(db, occupation_id))
    rows += [d for d in occupations_repository.work_style_descriptors(db, occupation_id)]
    for descriptor in rows:
        if not is_reported(descriptor) or descriptor.rating is None:
            continue
        key = descriptor.name.casefold()
        # Prefer the importance-scale row when the same descriptor appears on several scales.
        if key not in unique or descriptor.scale in ("IM", "WI"):
            unique[key] = descriptor
    return unique


def analyze(db: Session, user_id: int, request: SkillGapRequest) -> dict:
    occupation = None
    matched_from = None
    if request.occupation_id:
        occupation = occupations_repository.get_active(db, request.occupation_id)
        if not occupation:
            raise NotFoundError("Occupation not found")
    elif request.occupation_title:
        occupation = occupations_repository.find_by_title_or_code(db, request.occupation_title)
        if not occupation:
            matches = occupations_repository.search(db, request.occupation_title, 1)
            occupation = matches[0] if matches else None
            matched_from = request.occupation_title if occupation else None

    if not occupation:
        custom = (
            occupations_repository.find_custom_occupation(db, user_id, request.occupation_title)
            if request.occupation_title else None
        )
        return {
            "occupation": custom.title if custom else request.occupation_title,
            "strengths": [],
            "gaps": [],
            "focus": [],
            "suggestions": [],
            "source": "Not verified against O*NET",
            "notice": UNVERIFIED_NOTICE,
        }

    phrases = [str(skill).strip() for skill in request.current_skills if str(skill).strip()]
    unique = _descriptors(db, occupation.id)
    names = {key: descriptor.name for key, descriptor in unique.items()}
    matched_by: dict[str, list[str]] = {}
    unmatched: list[str] = []
    tools = [d.name for d in db.query(Descriptor).filter_by(occupation_id=occupation.id, category="Technology Skills")
             if len(d.name) >= 3]
    tools_known: list[str] = []
    for phrase in phrases:
        keys = match_descriptors(phrase, names)
        found_tools = match_tools(phrase, tools)
        for key in keys:
            matched_by.setdefault(key, []).append(phrase)
        for tool in found_tools:
            if tool not in tools_known:
                tools_known.append(tool)
        if not keys and not found_tools:
            unmatched.append(phrase)

    strengths, gaps = [], []
    for key, descriptor in unique.items():
        item = {
            "name": descriptor.name,
            "rating": descriptor.rating,
            "scale": descriptor.scale,
            "category": descriptor.category,
        }
        if key in matched_by:
            item["matched_from"] = matched_by[key]
            strengths.append(item)
        else:
            gaps.append(item)

    notice = MATCH_NOTICE
    if matched_from:
        notice = f'"{matched_from}" is not an exact O*NET title; showing the closest match, {occupation.title}. {notice}'

    level = effective_level(db, user_id)
    gaps.sort(key=lambda item: item["rating"] or 0, reverse=True)
    strengths.sort(key=lambda item: item["rating"] or 0, reverse=True)
    count = LEVELS[level]["focus_gaps"]
    # Prefer skills and knowledge a learner can build; innate abilities (like Near Vision) only fill any remaining slots.
    learnable = [g for g in gaps if g["category"] != "Abilities"]
    focus = (learnable + [g for g in gaps if g["category"] == "Abilities"])[:count]
    guidance = {
        "beginner": f"New to this? Do not try to learn everything. Start with just these {count} skills, one at a time.",
        "intermediate": f"Focus on these {count} skills next. They matter most for this career and you have not listed them.",
        "advanced": f"Your priority list: the {count} most important skills you have not shown evidence for.",
    }[level]
    suggestions = [
        {"id": item.id, "title": item.title}
        for item in occupations_repository.search(db, request.occupation_title or occupation.title, 6)
        if item.id != occupation.id
    ][:5]
    return {
        "occupation": occupation.title,
        "occupation_id": occupation.id,
        "source_url": f"https://www.onetonline.org/link/summary/{occupation.onet_soc_code}",
        "level": level,
        "focus": focus,
        "guidance": guidance,
        "strengths": strengths,
        "gaps": gaps,
        "tools_known": tools_known[:12],
        "unmatched": unmatched,
        "suggestions": suggestions,
        "notice": notice,
        "source": "Official O*NET descriptors" if unique else "No imported O*NET descriptors",
    }


def save_assessment(db: Session, user_id: int, request: SkillAssessmentRequest):
    item = repository.add_assessment(db, user_id, request.occupation_title, request.skill_name, request.rating)
    db.commit()
    db.refresh(item)
    return item


def list_assessments(db: Session, user_id: int):
    return repository.list_assessments(db, user_id)
