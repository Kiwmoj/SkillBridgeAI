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
from apps.backend.services.careers.pathways import pathways
from apps.backend.services.careers.profile import build_profile
from apps.backend.services.levels import effective_level, normalize

SOURCE_LABEL = "Built from official O*NET data for this occupation (not AI-generated)."


def _known(name: str, current: set[str]) -> bool:
    return name.casefold() in current


LEVEL_INTRO = {
    "beginner": "Written for a beginner: no prior experience needed. Take one small step at a time.",
    "intermediate": "Written for an intermediate learner: it builds on the basics you already know.",
    "advanced": "Written for an advanced learner: it focuses on depth, specialization and leadership.",
}


def build_source_plan(profile: dict, current_skills: list[str], level: str = "beginner") -> tuple[str, list[str]]:
    """Return (readable plan, activity titles) from a career profile, adapted to the learner's level."""
    level = normalize(level)
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

    knowledge = [k for k in profile["knowledge"] if not _known(k["name"], current)]
    skills = [s for s in profile["skills"] if not _known(s["name"], current)]
    tasks = profile["tasks"]
    tools = profile["technology"]["in_demand"] or profile["technology"]["other"]
    ways = [p for p in pathways(profile) if p["id"] in ("university", "vocational", "apprenticeship")]
    route_lines = [f"{p['label']}: {p['summary']}" + (f" ({p['percent_of_workers']}% of workers)"
                                                       if p["percent_of_workers"] else "") for p in ways]

    if level == "beginner":
        description = (profile["occupation"].get("description") or "").strip()
        steps.append(("Get to know this career", [description or "Read the career profile in Career Explorer."]
                      + [item for item in prep if item]))
        steps.append(("Learn the basics, one idea at a time",
                      [f"Start with a beginner introduction to {k['name']}" for k in knowledge[:3]]))
        steps.append(("Practise simple skills", [f"Try one easy exercise in {s['name']}" for s in skills[:3]]))
        steps.append(("Try one real task, with guidance",
                      [f"Read this task and rewrite it in your own words: {task}" for task in tasks[:1]]))
        steps.append(("Choose how you want to learn", route_lines))
        steps.append(("Take your first steps", [
            "Save one career and one opportunity that interests you under Opportunities",
            "Write down one question you still have and look it up",
        ]))
    elif level == "intermediate":
        steps.append(("Understand the requirements", prep or ["Review the career profile in Career Explorer."]))
        steps.append(("Fill your knowledge gaps", [f"Learn {k['name']}" for k in knowledge[:4]]))
        steps.append(("Develop core skills", [f"Practise {s['name']} with a hands-on exercise" for s in skills[:5]]))
        steps.append(("Practise with real work tasks", [f"Project: {task}" for task in tasks[:3]]))
        steps.append(("Learn the tools used on the job", [f"Get hands-on with {tool}" for tool in tools[:4]]))
        steps.append(("Choose and compare pathways", route_lines))
        steps.append(("Earn credentials and apply", [
            "Shortlist programs, certifications or apprenticeships under Opportunities",
            "Add a portfolio piece showing your best project",
            "Save at least one opportunity and update its status under Opportunities",
        ]))
    else:
        top = sorted(profile["skills"], key=lambda s: s["importance"] or 0, reverse=True)
        steps.append(("Audit your strengths against the top requirements",
                      [f"Rate yourself on {s['name']} and list evidence of your level" for s in top[:4]]))
        steps.append(("Deepen specialist knowledge", [f"Go deeper on {k['name']}: read advanced material and "
                                                      "apply it to a real case" for k in knowledge[:3]]))
        steps.append(("Capstone work with real constraints", [
            f"Capstone: {task} Add constraints such as time, budget, quality metrics or users." for task in tasks[:3]]))
        steps.append(("Master professional tools", [f"Reach expert level with {tool}" for tool in tools[:3]]))
        steps.append(("Specialize and lead", [
            "Choose one specialization and define what makes your work stand out",
            "Mentor or teach someone else and write up what you learned",
        ]))
        steps.append(("Credentials and next roles", route_lines + [
            "Add a case study with measurable results to your portfolio",
            "Shortlist advanced certifications or senior roles under Opportunities",
        ]))

    lines = [f"Learning roadmap: {occupation}", f"Level: {level.title()}", LEVEL_INTRO[level], SOURCE_LABEL, ""]
    activities: list[str] = []
    for number, (title, items) in enumerate(steps, start=1):
        items = [item for item in items if item]
        if not items:
            continue
        lines.append(f"Step {number}: {title}")
        lines.extend(f"  • {item}" for item in items)
        lines.append("")
        activities.extend(f"Step {number}: {item}"[:255] for item in items
                          if not item.startswith(("Most common", "Job Zone", "Read the career profile"))
                          and not item.startswith(tuple(f"{p['label']}:" for p in ways))
                          and item != (profile["occupation"].get("description") or "").strip())
    if current:
        lines.append("Skipped because you already reported them: " + ", ".join(sorted(current_skills)))
    return "\n".join(lines).strip(), activities


def create_roadmap(db: Session, user: User, request: RoadmapRequest) -> dict:
    occupation = resolve_occupation(db, request.occupation_id, request.occupation_title)
    if not ai_service.status().get("configured"):
        if occupation is None:
            raise NotFoundError("No imported occupation matches. Pick one in Career Explorer first.")
        profile = build_profile(db, occupation.id)
        content, activity_titles = build_source_plan(profile, request.current_skills, effective_level(db, user.id))
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
            "sources": records, "generated": generated, "activities": len(activity_titles),
            "level": effective_level(db, user.id)}


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
