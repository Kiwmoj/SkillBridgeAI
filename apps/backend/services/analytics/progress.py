"""Per-user progress summary shown on the dashboard and analytics page."""
from sqlalchemy.orm import Session

from apps.backend.repositories import analytics as repository
from apps.backend.repositories import opportunities as opportunities_repository
from apps.backend.repositories import portfolio as portfolio_repository
from apps.backend.repositories import roadmaps as roadmaps_repository


def summary(db: Session, user_id: int) -> dict:
    projects = repository.list_projects(db, user_id)
    activities = repository.list_activities(db, user_id)
    return {
        "saved_roadmaps": roadmaps_repository.count_roadmaps(db, user_id),
        "project_total": len(projects),
        "projects_planned": sum(project.status == "planned" for project in projects),
        "projects_in_progress": sum(project.status == "in_progress" for project in projects),
        "projects_completed": sum(project.status == "completed" for project in projects),
        "learning_activity_total": len(activities),
        "learning_activities_completed": sum(activity.status == "completed" for activity in activities),
        "skill_assessment_total": repository.count_assessments(db, user_id),
        "saved_opportunities": opportunities_repository.count_saved(db, user_id),
        "portfolio_total": portfolio_repository.count_items(db, user_id),
    }
