"""Skill levels: stored on the user's profile and used to adapt roadmaps, projects, assessments and AI answers."""
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import ValidationFailure
from apps.backend.repositories import users as users_repository

DEFAULT_LEVEL = "beginner"

LEVELS: dict[str, dict] = {
    "beginner": {
        "label": "Beginner",
        "summary": "New to this field. Plain-language explanations and small guided steps, no prior knowledge assumed.",
        "job_zones": (1, 2, 3),
        "focus_gaps": 3,
        "ai_note": (
            "The learner is a BEGINNER with no assumed prior knowledge. Use plain everyday language, define every "
            "technical term the first time it appears, give small concrete first steps, and be encouraging."
        ),
    },
    "intermediate": {
        "label": "Intermediate",
        "summary": "Some experience. Practical exercises and projects that build on what you already know.",
        "job_zones": (3, 4),
        "focus_gaps": 5,
        "ai_note": (
            "The learner is INTERMEDIATE: they know the basics. Skip introductions, focus on practical exercises, "
            "realistic projects and closing specific skill gaps."
        ),
    },
    "advanced": {
        "label": "Advanced",
        "summary": "Experienced. Challenging projects, specialization and leadership-level pathways.",
        "job_zones": (4, 5),
        "focus_gaps": 8,
        "ai_note": (
            "The learner is ADVANCED and experienced. Be concise and technical, emphasise specialization, "
            "trade-offs, quality criteria, leadership and challenging projects."
        ),
    },
}


def normalize(level: str | None) -> str:
    return level if level in LEVELS else DEFAULT_LEVEL


def get_level(db: Session, user_id: int) -> str | None:
    profile = users_repository.get_profile(db, user_id)
    return profile.skill_level if profile and profile.skill_level in LEVELS else None


def effective_level(db: Session, user_id: int) -> str:
    """The saved level, or beginner (the most supportive default) until the user chooses."""
    return normalize(get_level(db, user_id))


def set_level(db: Session, user_id: int, level: str) -> str:
    if level not in LEVELS:
        raise ValidationFailure("Choose beginner, intermediate or advanced.")
    profile = users_repository.get_profile(db, user_id) or users_repository.add_profile(db, user_id)
    profile.skill_level = level
    db.commit()
    return level


def describe(db: Session, user_id: int) -> dict:
    chosen = get_level(db, user_id)
    return {
        "skill_level": chosen,
        "effective_level": normalize(chosen),
        "levels": [{"id": key, "label": value["label"], "summary": value["summary"]} for key, value in LEVELS.items()],
    }


def prompt_note(db: Session, user_id: int) -> str:
    return LEVELS[effective_level(db, user_id)]["ai_note"]
