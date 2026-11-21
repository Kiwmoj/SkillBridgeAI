from fastapi import APIRouter

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.skills import SkillAssessmentRequest, SkillGapRequest
from apps.backend.services.skills import gap_analysis

router = APIRouter(tags=["skills"])


@router.post("/skill-gap")
def skill_gap(request: SkillGapRequest, user: CurrentUser, db: DbSession):
    return gap_analysis.analyze(db, user.id, request)


@router.post("/assessments")
def save_assessment(request: SkillAssessmentRequest, user: CurrentUser, db: DbSession):
    return gap_analysis.save_assessment(db, user.id, request)


@router.get("/assessments")
def list_assessments(user: CurrentUser, db: DbSession):
    return gap_analysis.list_assessments(db, user.id)
