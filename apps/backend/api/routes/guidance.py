from fastapi import APIRouter

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.schemas.guidance import AIGenerateRequest
from apps.backend.services.ai import guidance

router = APIRouter(prefix="/ai", tags=["guidance"])


@router.post("/generate")
def ai_generate(request: AIGenerateRequest, user: CurrentUser, db: DbSession):
    return guidance.answer(db, user, request)
