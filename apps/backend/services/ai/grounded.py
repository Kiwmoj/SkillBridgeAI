"""Retrieve sources, generate with the configured provider, and record usage — in one place.

Guidance, roadmaps, projects, and portfolio review all go through ``generate_grounded`` or
``generate_from_image`` so provider failures, usage accounting, and source handling behave identically.
"""
from collections.abc import Callable
from time import monotonic

from sqlalchemy.orm import Session

from apps.backend.core.exceptions import ExternalServiceError
from apps.backend.models import User
from apps.backend.repositories import analytics as usage_repository
from apps.backend.services.ai.providers import AIProviderError
from apps.backend.services.ai.retrieval import retrieval_service, source_context
from apps.backend.services.ai.service import ai_service


def _record(db: Session, user: User, feature: str, success: bool, started: float) -> None:
    latency_ms = max(0, int((monotonic() - started) * 1000))
    usage_repository.record_ai_usage(db, user.id, ai_service.active, feature, success, latency_ms)


def generate_grounded(db: Session, user: User, feature: str, query: str,
                      build_prompt: Callable[[str], str]) -> tuple[str, list[dict]]:
    """Return (answer, sources). ``build_prompt`` receives the formatted source context."""
    started = monotonic()
    records = retrieval_service.search(db, query)
    prompt = build_prompt(source_context(records))
    try:
        answer = ai_service.generate(prompt)
    except AIProviderError as exc:
        _record(db, user, feature, False, started)
        raise ExternalServiceError(str(exc)) from exc
    _record(db, user, feature, True, started)
    return answer, records


def generate_from_image(db: Session, user: User, feature: str, prompt: str,
                        image_bytes: bytes, mime_type: str) -> str:
    started = monotonic()
    try:
        answer = ai_service.generate_with_image(prompt, image_bytes, mime_type)
    except AIProviderError as exc:
        _record(db, user, feature, False, started)
        raise ExternalServiceError(str(exc)) from exc
    _record(db, user, feature, True, started)
    return answer
