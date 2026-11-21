"""Career guidance answers.

When an AI provider is configured, answers are generated and grounded in retrieved sources.
When none is configured, the endpoint still returns useful, verifiable information compiled directly
from the retrieved official/reviewed sources — clearly marked as not AI-generated (never fabricated).
"""
from sqlalchemy.orm import Session

from apps.backend.models import User
from apps.backend.schemas.guidance import AIGenerateRequest
from apps.backend.services.ai.grounded import generate_grounded
from apps.backend.services.ai.retrieval import retrieval_service
from apps.backend.services.ai.service import ai_service


def _compiled_from_sources(records: list[dict]) -> str:
    if not records:
        return (
            "AI text generation is not enabled on this server, and no official sources matched this "
            "question. Try a specific occupation name (for example \"Registered Nurses\"), or ask an "
            "administrator to import the O*NET dataset."
        )
    return (
        "AI text generation is not enabled on this server, so this answer is compiled directly from "
        "official O*NET and reviewed community sources (it is not AI-generated). See the references below."
    )


def answer(db: Session, user: User, request: AIGenerateRequest) -> dict:
    # No provider configured: return a verifiable, source-based response instead of an error.
    if not ai_service.status().get("configured"):
        records = retrieval_service.search(db, request.question)
        return {
            "answer": _compiled_from_sources(records),
            "sources": records,
            "generated": False,
            "retrieved": bool(records),
            "provider": "sources",
        }

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
