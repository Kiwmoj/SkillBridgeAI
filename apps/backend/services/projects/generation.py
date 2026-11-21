"""Project Studio: create, plan, and complete career projects inside the platform.

With an AI provider configured, the brief is generated. Without one, the brief is built from real
O*NET task statements for the chosen occupation and labelled as such. Every project gets a
milestone checklist that drives its in-platform progress.
"""
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import BadRequest, NotFoundError
from apps.backend.models import Portfolio, User
from apps.backend.repositories import projects as repository
from apps.backend.schemas.projects import ProjectRequest, ProjectUpdateRequest
from apps.backend.services.ai.grounded import generate_grounded
from apps.backend.services.ai.service import ai_service
from apps.backend.services.careers.explorer import resolve_occupation
from apps.backend.services.careers.profile import build_profile

PROJECT_STATUSES = {"planned", "in_progress", "completed"}
DEFAULT_MILESTONES = (
    "Define the goal, audience, and success criteria",
    "Research how professionals approach this work",
    "Build a first version",
    "Get feedback and improve it",
    "Document the process and results for your portfolio",
)


def _milestones(titles) -> list[dict]:
    return [{"title": title[:255], "done": False} for title in titles]


def build_source_brief(profile: dict, title: str, experience: str) -> tuple[str, list[dict]]:
    occupation = profile["occupation"]["title"]
    tasks = profile["tasks"][:3]
    skills = [s["name"] for s in profile["skills"][:5]]
    tools = (profile["technology"]["in_demand"] or profile["technology"]["other"])[:3]
    lines = [
        title,
        f"Built from official O*NET task statements for {occupation} (not AI-generated).",
        "",
        "Goal: complete a small, realistic piece of work modelled on what this occupation actually does.",
        "",
        "Real tasks this project simulates:",
        *[f"  • {task}" for task in tasks],
        "",
        "Skills you will practise: " + (", ".join(skills) if skills else "see the career profile"),
    ]
    if tools:
        lines.append("Tools professionals use for this work: " + ", ".join(tools))
    if experience:
        lines += ["", f"Your starting point: {experience}"]
    lines += ["", "Deliverable: a short write-up or artefact you can add to your portfolio."]
    milestones = _milestones([f"Plan how you will approach: {tasks[0]}" if tasks else DEFAULT_MILESTONES[0],
                              *[f"Complete: {task}" for task in tasks],
                              "Write up what you did, what you learned, and the result",
                              "Add the finished work to your portfolio"])
    return "\n".join(lines), milestones


def serialize(project) -> dict:
    milestones = project.milestones or []
    return {
        "id": project.id, "title": project.title, "description": project.description, "status": project.status,
        "notes": project.notes, "milestones": milestones,
        "progress": round(100 * sum(m.get("done", False) for m in milestones) / len(milestones)) if milestones else 0,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


def create_project(db: Session, user: User, request: ProjectRequest) -> dict:
    occupation_text = request.occupation.strip()
    if not ai_service.status().get("configured"):
        occupation = resolve_occupation(db, request.occupation_id, occupation_text)
        if occupation is None:
            raise NotFoundError("No imported occupation matches. Pick one in Career Explorer first.")
        title = request.title.strip() if request.title else f"{occupation.title} practice project"
        description, milestones = build_source_brief(build_profile(db, occupation.id), title, request.experience)
        records = [{"id": "S1", "source_type": "onet", "title": occupation.title,
                    "url": f"https://www.onetonline.org/link/summary/{occupation.onet_soc_code}",
                    "reference": "O*NET® Database, U.S. Department of Labor/ETA", "text": occupation.description or ""}]
        generated = False
    else:
        title = request.title.strip() if request.title else f"{occupation_text} portfolio project"

        def prompt(sources: str) -> str:
            return (
                f"Generate a realistic, ethical project for a student pursuing {occupation_text}. "
                f"Project theme: {title}. Student-provided experience and skills: "
                f"{request.experience or 'Not provided'}. Include difficulty, materials, objectives, phases, "
                "outcomes and portfolio presentation. Label this as AI-generated guidance.\n"
                f"{sources}"
            )

        description, records = generate_grounded(db, user, "project_generator", occupation_text, prompt)
        milestones = _milestones(DEFAULT_MILESTONES)
        generated = True
    project = repository.add_project(db, user.id, title[:255], description)
    project.milestones = milestones
    db.commit()
    db.refresh(project)
    return {**serialize(project), "sources": records, "generated": generated}


def list_projects(db: Session, user_id: int) -> list[dict]:
    return [serialize(project) for project in repository.list_projects(db, user_id)]


def update_project(db: Session, user_id: int, project_id: int, request: ProjectUpdateRequest) -> dict:
    project = repository.get_project(db, user_id, project_id)
    if request.status is not None and request.status not in PROJECT_STATUSES:
        raise BadRequest("Invalid project status")
    if not project:
        raise NotFoundError("Project not found")
    if request.title is not None:
        project.title = request.title
    if request.notes is not None:
        project.notes = request.notes
    if request.milestones is not None:
        project.milestones = [m.model_dump() for m in request.milestones]
        milestones = project.milestones
        if request.status is None and milestones:
            done = sum(m["done"] for m in milestones)
            project.status = "completed" if done == len(milestones) else "in_progress" if done else "planned"
    if request.status is not None:
        project.status = request.status
    db.commit()
    db.refresh(project)
    return serialize(project)


def delete_project(db: Session, user_id: int, project_id: int) -> None:
    project = repository.get_project(db, user_id, project_id)
    if not project:
        raise NotFoundError("Project not found")
    # Keep portfolio pieces; just unlink them from the deleted project.
    for item in db.query(Portfolio).filter_by(user_id=user_id, project_id=project_id):
        item.project_id = None
    db.delete(project)
    db.commit()
