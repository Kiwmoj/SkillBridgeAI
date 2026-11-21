"""Administrator overview of community, consent, dataset, model, and AI usage figures."""
from sqlalchemy.orm import Session

from apps.backend.repositories import analytics as analytics_repository
from apps.backend.repositories import community as community_repository
from apps.backend.repositories import training as training_repository
from apps.backend.services.training.pipeline import eligible_record_count


def overview(db: Session) -> dict:
    contributions = community_repository.list_all_contributions(db)
    consents = community_repository.list_consents(db)
    requests, successful = analytics_repository.usage_totals(db)
    statuses = [item.review_status for item in contributions]
    return {
        "total_contributions": len(contributions),
        "pending": statuses.count("pending"),
        "approved": statuses.count("approved"),
        "rejected": statuses.count("rejected"),
        "training_consent_users": sum(consent.consent_enabled for consent in consents),
        "training_consent_records": sum(item.consent_to_training for item in contributions),
        "training_eligible_records": eligible_record_count(db),
        "approved_knowledge_records": community_repository.count_approved(db),
        **training_repository.counts(db),
        "ai_requests": requests,
        "ai_requests_successful": successful,
    }
