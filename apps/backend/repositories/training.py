from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.backend.models import (
    CONSENT_VERSION,
    ApprovedKnowledge,
    CommunityContribution,
    DatasetRecord,
    DatasetVersion,
    ModelVersion,
    TrainingConsent,
    TrainingHistory,
)


def eligible_training_rows(db: Session) -> list[tuple[CommunityContribution, ApprovedKnowledge]]:
    """Approved, de-identified, rights-confirmed contributions whose owners currently consent to training."""
    rows = db.query(CommunityContribution, ApprovedKnowledge).join(
        ApprovedKnowledge, ApprovedKnowledge.source_contribution_id == CommunityContribution.id
    ).join(TrainingConsent, TrainingConsent.user_id == CommunityContribution.user_id).filter(
        CommunityContribution.review_status == "approved",
        CommunityContribution.consent_to_training.is_(True),
        CommunityContribution.deidentified.is_(True),
        CommunityContribution.copyright_confirmed.is_(True),
        TrainingConsent.consent_enabled.is_(True),
        TrainingConsent.disclosure_version == CONSENT_VERSION,
    ).order_by(CommunityContribution.id).all()
    return [(contribution, approved) for contribution, approved in rows]


def get_dataset(db: Session, dataset_id: int) -> DatasetVersion | None:
    return db.get(DatasetVersion, dataset_id)


def get_dataset_by_name(db: Session, name: str) -> DatasetVersion | None:
    return db.query(DatasetVersion).filter_by(name=name).first()


def latest_imported_dataset(db: Session) -> DatasetVersion | None:
    return db.query(DatasetVersion).filter_by(status="imported").order_by(DatasetVersion.id.desc()).first()


def add_dataset(db: Session, name: str, status: str, train_count: int, validation_count: int) -> DatasetVersion:
    dataset = DatasetVersion(name=name, status=status, train_count=train_count, validation_count=validation_count)
    db.add(dataset)
    return dataset


def list_datasets(db: Session) -> list[DatasetVersion]:
    return db.query(DatasetVersion).order_by(DatasetVersion.created_at.desc()).all()


def drafts_containing(db: Session, contribution_ids) -> list[DatasetVersion]:
    return list(db.scalars(select(DatasetVersion).where(
        DatasetVersion.status == "draft",
        DatasetVersion.id.in_(select(DatasetRecord.dataset_version_id)
                              .where(DatasetRecord.contribution_id.in_(contribution_ids))),
    )))


def delete_dataset_records(db: Session, dataset_id: int) -> None:
    db.execute(delete(DatasetRecord).where(DatasetRecord.dataset_version_id == dataset_id))


def add_record(db: Session, dataset_id: int, record: dict) -> DatasetRecord:
    item = DatasetRecord(
        dataset_version_id=dataset_id,
        contribution_id=record["contribution_id"],
        content_hash=record["content_hash"],
        title=record["title"],
        text=record["text"],
        category=record["category"],
        source_reference=record["source_reference"],
        quality_rating=record["quality_rating"],
        split=record["split"],
    )
    db.add(item)
    return item


def list_records(db: Session, dataset_id: int) -> list[DatasetRecord]:
    return (
        db.query(DatasetRecord).filter_by(dataset_version_id=dataset_id)
        .order_by(DatasetRecord.split, DatasetRecord.content_hash).all()
    )


def add_history(db: Session, dataset_id: int, action: str, status: str, details: str | None = None) -> TrainingHistory:
    item = TrainingHistory(dataset_version_id=dataset_id, action=action, status=status, details=details)
    db.add(item)
    return item


def list_history(db: Session) -> list[TrainingHistory]:
    return db.query(TrainingHistory).order_by(TrainingHistory.created_at.desc()).all()


def list_models(db: Session) -> list[ModelVersion]:
    return db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()


def get_model_by_name(db: Session, name: str) -> ModelVersion | None:
    return db.query(ModelVersion).filter_by(name=name).first()


def add_model(db: Session, name: str, provider: str, status: str, evaluation_summary: str | None) -> ModelVersion:
    item = ModelVersion(name=name, provider=provider, status=status, evaluation_summary=evaluation_summary)
    db.add(item)
    return item


def counts(db: Session) -> dict[str, int]:
    return {
        "dataset_versions": db.query(DatasetVersion).count(),
        "dataset_records": db.query(DatasetRecord).count(),
        "training_history_entries": db.query(TrainingHistory).count(),
        "model_versions": db.query(ModelVersion).count(),
    }
