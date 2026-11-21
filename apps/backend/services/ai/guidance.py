"""Career guidance answers grounded in retrieved sources (Career Reality Check and skill-gap follow-ups)."""
from sqlalchemy.orm import Session

from apps.backend.models import User
from apps.backend.schemas.guidance import AIGenerateRequest
from apps.backend.services.ai.grounded import generate_grounded
from apps.backend.services.ai.service import ai_service


def answer(db: Session, user: User, request: AIGenerateRequest) -> dict:
    def prompt(sources: str) -> str:
        return (
            f"Purpose: {request.purpose}\n"
            f"Question: {request.question}\n\n"
            "Provide educational career guidance. Do not guarantee admission or employment.\n\n"
            f"{sources}"
        )

    text, records = generate_grounded(db, user, "career_guidance", request.question, prompt)
    return {
        "answer": text,
        "sources": records,
        "generated": True,
        "retrieved": bool(records),
        "provider": ai_service.active,
    }
