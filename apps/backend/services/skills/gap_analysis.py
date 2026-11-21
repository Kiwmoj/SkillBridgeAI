"""Compare self-reported skills with imported O*NET descriptors for an occupation."""
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import NotFoundError
from apps.backend.repositories import occupations as occupations_repository
from apps.backend.repositories import skills as repository
from apps.backend.schemas.skills import SkillAssessmentRequest, SkillGapRequest
from apps.backend.services.careers.explorer import is_reported
from apps.backend.services.levels import LEVELS, effective_level

UNVERIFIED_NOTICE = (
    "This occupation is not represented by imported official O*NET data. "
    "Use AI guidance only as general, unverified career information."
)
MATCH_NOTICE = "Matches are self-reported. A gap means a descriptor was not reported, not that ability was tested."


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
            "source": "Not verified against O*NET",
            "notice": UNVERIFIED_NOTICE,
        }

    current = {str(skill).strip().lower() for skill in request.current_skills if str(skill).strip()}
    unique = {}
    for descriptor in occupations_repository.skill_descriptors(db, occupation.id):
        if not is_reported(descriptor):
            continue
        key = descriptor.name.casefold()
        # Prefer the importance-scale row when the same descriptor appears on several scales.
        if key not in unique or descriptor.scale == "IM":
            unique[key] = descriptor
    strengths, gaps = [], []
    for descriptor in unique.values():
        item = {
            "name": descriptor.name,
            "rating": descriptor.rating,
            "scale": descriptor.scale,
            "category": descriptor.category,
        }
        # A listed skill counts if it names the descriptor or mentions it in a longer phrase.
        known = descriptor.name.casefold() in current or any(descriptor.name.casefold() in text for text in current)
        (strengths if known else gaps).append(item)
    notice = MATCH_NOTICE
    if matched_from:
        notice = f'"{matched_from}" is not an exact O*NET title; showing the closest match, {occupation.title}. {MATCH_NOTICE}'
    level = effective_level(db, user_id)
    gaps.sort(key=lambda item: item["rating"] or 0, reverse=True)
    strengths.sort(key=lambda item: item["rating"] or 0, reverse=True)
    count = LEVELS[level]["focus_gaps"]
    guidance = {
        "beginner": f"New to this? Do not try to learn everything. Start with just these {count} skills, one at a time.",
        "intermediate": f"Focus on these {count} skills next. They matter most for this career and you have not listed them.",
        "advanced": f"Your priority list: the {count} most important skills you have not shown evidence for.",
    }[level]
    return {
        "occupation": occupation.title,
        "source_url": f"https://www.onetonline.org/link/summary/{occupation.onet_soc_code}",
        "level": level,
        "focus": gaps[:count],
        "guidance": guidance,
        "strengths": strengths,
        "gaps": gaps,
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
