import hashlib
import re
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from backend.models import ApprovedKnowledge, CommunityContribution, DatasetRecord, DatasetVersion, TrainingConsent, TrainingHistory
from backend.schemas import CONSENT_VERSION

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

def sanitize_for_training(text: str) -> str:
    sanitized = EMAIL_RE.sub("[REDACTED_EMAIL]", text or "")
    sanitized = PHONE_RE.sub("[REDACTED_PHONE]", sanitized)
    sanitized = SSN_RE.sub("[REDACTED_SSN]", sanitized)
    return sanitized

def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def build_reviewed_dataset(db: Session, name: str) -> dict:
    eligible = db.query(CommunityContribution, ApprovedKnowledge).join(
        ApprovedKnowledge, ApprovedKnowledge.source_contribution_id == CommunityContribution.id
    ).join(TrainingConsent, TrainingConsent.user_id == CommunityContribution.user_id).filter(
        CommunityContribution.review_status == "approved",
        CommunityContribution.consent_to_training.is_(True),
        CommunityContribution.deidentified.is_(True),
        CommunityContribution.copyright_confirmed.is_(True),
        TrainingConsent.consent_enabled.is_(True),
        TrainingConsent.disclosure_version == CONSENT_VERSION,
    ).order_by(CommunityContribution.id).all()
    records = []
    seen = set()
    for contribution, item in eligible:
        sanitized = sanitize_for_training(item.body)
        digest = stable_hash(" ".join(sanitized.casefold().split()))
        if digest in seen:
            continue
        seen.add(digest)
        records.append({
            "contribution_id": contribution.id,
            "title": sanitize_for_training(item.title),
            "text": sanitized,
            "category": item.category,
            "source_reference": sanitize_for_training(item.source_reference or ""),
            "quality_rating": item.quality_score,
            "content_hash": digest,
        })
    records.sort(key=lambda record: record["content_hash"])
    if not records:
        train = []
        validation = []
    elif len(records) == 1:
        train = records
        validation = []
    else:
        split_index = max(1, min(len(records) - 1, int(len(records) * 0.8)))
        train = records[:split_index]
        validation = records[split_index:]
    for record in train:
        record["split"] = "train"
    for record in validation:
        record["split"] = "validation"
    return {
        "name": name,
        "status": "draft",
        "eligible_before_dedup": len(eligible),
        "train_count": len(train),
        "validation_count": len(validation),
        "records": records,
    }


def invalidate_datasets(db: Session, contribution_ids) -> None:
    affected = db.scalars(select(DatasetVersion).where(
        DatasetVersion.status == "draft",
        DatasetVersion.id.in_(select(DatasetRecord.dataset_version_id)
                              .where(DatasetRecord.contribution_id.in_(contribution_ids))),
    )).all()
    for dataset in affected:
        db.execute(delete(DatasetRecord).where(DatasetRecord.dataset_version_id == dataset.id))
        dataset.status = "revoked"
        dataset.train_count = dataset.validation_count = 0
        db.add(TrainingHistory(dataset_version_id=dataset.id, action="dataset_revoked", status="revoked"))
