"""Generate, store, and manage learning roadmaps and their activities.

With an AI provider configured, roadmaps are generated and grounded in retrieved sources. Without
one, the roadmap is assembled directly from the occupation's official O*NET profile and labelled as
such. Either way, each step is saved as a learning activity so progress can be tracked in-platform.
"""
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import NotFoundError
from apps.backend.models import User
from apps.backend.repositories import roadmaps as repository
from apps.backend.schemas.roadmaps import LearningActivityRequest, RoadmapRequest
from apps.backend.services.ai.grounded import generate_grounded
from apps.backend.services.ai.service import ai_service
from apps.backend.services.careers.explorer import resolve_occupation
from apps.backend.services.careers.profile import build_profile

SOURCE_LABEL = "Built from official O*NET data for this occupation (not AI-generated)."


def _known(name: str, current: set[str]) -> bool:
    return name.casefold() in current


def build_source_plan(profile: dict, current_skills: list[str]) -> tuple[str, list[str]]:
    """Return (readable plan, activity titles) from a career profile."""
    current = {skill.casefold().strip() for skill in current_skills}
    occupation = profile["occupation"]["title"]
    steps: list[tuple[str, list[str]]] = []

    education = profile["education"][:3]
    zone = profile["job_zone"]
    prep = []
    if education:
        prep.append("Most common education among workers: " + "; ".join(
            f"{e['label']} ({e['percent_of_workers']}%)" for e in education))
    if zone:
        prep.append(f"{zone['name']}. {zone['education'] or ''}".strip())
    steps.append(("Understand the requirements", prep or ["Review the career profile in Career Explorer."]))

    knowledge = [k for k in profile["knowledge"] if not _known(k["name"], current)][:4]
    steps.append(("Build foundational knowledge", [f"Learn {k['name']}" for k in knowledge]))

    skills = [s for s in profile["skills"] if not _known(s["name"], current)][:5]
    steps.append(("Develop core skills", [f"Practise {s['name']}" for s in skills]))

    tasks = profile["tasks"][:3]
    steps.append(("Practise with real work tasks", [f"Project: {task}" for task in tasks]))

    tools = profile["technology"]["in_demand"][:4] or profile["technology"]["other"][:4]
    steps.append(("Learn the tools used on the job", [f"Get hands-on with {tool}" for tool in tools]))

    steps.append(("Earn credentials and apply", [
        "Shortlist education or training         programs under Opportunities",
        "Add a portfolio piece showing your best project",
                "Save at least one opportunity and update its status under Opportunities",
    ]))

    lines = [f"Learning roadmap: {occupation}", SOURCE_LABEL, ""]
    activities: list[str] = []
    for number, (title, items) in enumerate(steps, start=1):
        items = [item for item in items if item]
        if not items:
            continue
        lines.append(f"Step {number}: {title}")
        lines.extend(f"  • {item}" for item in items)
        lines.append("")
        activities.extend(f"Step {number}: {item}"[:255] for item in items if not item.startswith("Most common")
                          and not item.startswith("Job Zone"))
    if current:
        lines.append("Skipped because you already reported them: " + ", ".join(sorted(current_skills)))
    return "\n".join(lines).strip(), activities


def create_roadmap(db: Session, user: User, request: RoadmapRequest) -> dict:
    occupation = resolve_occupation(db, request.occupation_id, request.occupation_title)
    if not ai_service.status().get("configured"):
        if occupation is None:
            raise NotFoundError("No imported occupation matches. Pick one in Career Explorer first.")
        profile = build_profile(db, occupation.id)
        content, activity_titles = build_source_plan(profile, request.current_skills)
        records = [{"id": "S1", "source_type": "onet", "title": occupation.title,
                    "reference": profile["attribution"]["credit"],
                    "url": f"https://www.onetonline.org/link/summary/{occupation.onet_soc_code}",
                    "text": occupation.description or "", "verified": True}]
        generated = False
        title = occupation.title
    else:
        def prompt(sources: str) -> str:
            return (
                f"Create an adaptive learning roadmap for {request.occupation_title}. "
                f"User interests: {request.interests or 'Not provided'}. "
                f"Current skills: {request.current_skills}. "
                "Include prerequisites, measurable objectives, time ranges, practice projects, and completion "
                "criteria. Consider college, vocational, apprenticeship and work-based paths where appropriate.\n"
                f"{sources}"
            )

        content, records = generate_grounded(db, user, "roadmap", request.occupation_title, prompt)
        activity_titles = []
        generated = True
        title = request.occupation_title.strip()

    roadmap = repository.add_roadmap(db, user.id, title, content, records)
    db.flush()
    for activity in activity_titles:
        repository.add_activity(db, user.id, roadmap.id, activity, "not_started", None)
    db.commit()
    db.refresh(roadmap)
    return {"id": roadmap.id, "occupation_title": roadmap.occupation_title, "content": content,
            "sources": records, "generated": generated, "activities": len(activity_titles)}


def list_roadmaps(db: Session, user_id: int) -> list[dict]:
    activities = repository.list_activities(db, user_id)
    counts: dict[int, list[int]] = {}
    for activity in activities:
        if activity.roadmap_id:
            done_total = counts.setdefault(activity.roadmap_id, [0, 0])
            done_total[1] += 1
            done_total[0] += activity.status == "completed"
    return [
        {
            "id": item.id,
            "occupation_title": item.occupation_title,
            "content": item.content,
            "sources": item.sources,
            "created_at": item.created_at.isoformat(),
            "completed_steps": counts.get(item.id, [0, 0])[0],
            "total_steps": counts.get(item.id, [0, 0])[1],
        }
        for item in repository.list_roadmaps(db, user_id)
    ]


def delete_roadmap(db: Session, user_id: int, roadmap_id: int) -> None:
    roadmap = repository.get_roadmap(db, user_id, roadmap_id)
    if not roadmap:
        raise NotFoundError("Roadmap not found")
    repository.delete_roadmap(db, roadmap)
    db.commit()


def _require_roadmap(db: Session, user_id: int, roadmap_id: int | None) -> None:
    if roadmap_id and not repository.get_roadmap(db, user_id, roadmap_id):
        raise NotFoundError("Roadmap not found")


def create_activity(db: Session, user_id: int, request: LearningActivityRequest):
    _require_roadmap(db, user_id, request.roadmap_id)
    item = repository.add_activity(db, user_id, request.roadmap_id, request.title, request.status, request.notes)
    db.commit()
    db.refresh(item)
    return item


def list_activities(db: Session, user_id: int):
    return repository.list_activities(db, user_id)


def update_activity(db: Session, user_id: int, activity_id: int, request: LearningActivityRequest):
    item = repository.get_activity(db, user_id, activity_id)
    if not item:
        raise NotFoundError("Learning activity not found")
    if "roadmap_id" in request.model_fields_set:
        _require_roadmap(db, user_id, request.roadmap_id)
        item.roadmap_id = request.roadmap_id
    item.title = request.title
    item.status = request.status
    item.notes = request.notes
    db.commit()
    db.refresh(item)
    return item
