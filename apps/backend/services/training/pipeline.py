"""Reviewed dataset drafts for a future, separately evaluated SkillBridge model.

Building a draft never trains, exports, deploys, or switches a model; it snapshots eligible,
consented, de-identified community knowledge with a deterministic train/validation split.
"""
import hashlib
import json

from sqlalchemy.orm import Session

from apps.backend.core.exceptions import BadRequest, ConflictError, NotFoundError
from apps.backend.repositories import community as community_repository
from apps.backend.repositories import training as repository
from apps.backend.schemas.training import ModelVersionRequest
from apps.backend.services.community.privacy import sanitize_for_training

TRAIN_FRACTION = 0.8
ONET_DATASET_PREFIX = "O*NET "


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_reviewed_dataset(db: Session, name: str) -> dict:
    eligible = repository.eligible_training_rows(db)
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
        train, validation = [], []
    elif len(records) == 1:
        train, validation = records, []
    else:
        split_index = max(1, min(len(records) - 1, int(len(records) * TRAIN_FRACTION)))
        train, validation = records[:split_index], records[split_index:]
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
    for dataset in repository.drafts_containing(db, contribution_ids):
        repository.delete_dataset_records(db, dataset.id)
        dataset.status = "revoked"
        dataset.train_count = dataset.validation_count = 0
        repository.add_history(db, dataset.id, "dataset_revoked", "revoked")


def eligible_record_count(db: Session) -> int:
    return build_reviewed_dataset(db, "count")["eligible_before_dedup"]


def create_draft(db: Session, name: str) -> dict:
    community_repository.lock_community_writes(db)
    name = name.strip()
    if name.upper().startswith(ONET_DATASET_PREFIX):
        raise BadRequest("The O*NET dataset prefix is reserved for reference imports.")
    if repository.get_dataset_by_name(db, name):
        raise ConflictError("Dataset version name already exists")
    snapshot = build_reviewed_dataset(db, name)
    dataset = repository.add_dataset(db, name, "draft", snapshot["train_count"], snapshot["validation_count"])
    db.flush()
    for record in snapshot["records"]:
        repository.add_record(db, dataset.id, record)
    repository.add_history(db, dataset.id, "dataset_snapshot", "draft", json.dumps({
        "eligible_before_dedup": snapshot["eligible_before_dedup"],
        "train_count": snapshot["train_count"],
        "validation_count": snapshot["validation_count"],
        "training_performed": False,
    }))
    db.commit()
    return {
        "id": dataset.id,
        "name": dataset.name,
        "status": dataset.status,
        "eligible_before_dedup": snapshot["eligible_before_dedup"],
        "train_count": snapshot["train_count"],
        "validation_count": snapshot["validation_count"],
        "training_performed": False,
    }


def draft_records(db: Session, dataset_id: int) -> dict:
    dataset = repository.get_dataset(db, dataset_id)
    if not dataset:
        raise NotFoundError("Dataset version not found")
    if dataset.status != "draft":
        raise ConflictError("This dataset is not an eligible training draft.")
    return {
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "status": dataset.status,
            "train_count": dataset.train_count,
            "validation_count": dataset.validation_count,
        },
        "records": [
            {
                "content_hash": record.content_hash,
                "title": record.title,
                "category": record.category,
                "quality_rating": record.quality_rating,
                "split": record.split,
            }
            for record in repository.list_records(db, dataset_id)
        ],
    }


def register_model(db: Session, request: ModelVersionRequest):
    if request.status == "evaluated" and not request.evaluation_summary:
        raise BadRequest("Record evaluation results before marking a model evaluated.")
    if repository.get_model_by_name(db, request.name):
        raise ConflictError("Model version name already exists")
    item = repository.add_model(db, request.name, request.provider, request.status, request.evaluation_summary)
    db.commit()
    db.refresh(item)
    return item
