from pathlib import Path
from threading import Lock

from fastapi import APIRouter, File, Query, UploadFile

from apps.backend.api.dependencies import AdminUser, DbSession
from apps.backend.core.exceptions import BadRequest, ConflictError, PayloadTooLarge
from apps.backend.repositories import training as training_repository
from apps.backend.schemas.community import ContributionReviewRequest
from apps.backend.schemas.training import DatasetBuildRequest, ModelVersionRequest
from apps.backend.services.analytics import dashboard
from apps.backend.services.careers.onet_import import OnetImportError, import_onet_zip, register_import
from apps.backend.services.community import contributions
from apps.backend.services.training import pipeline

router = APIRouter(prefix="/admin", tags=["administration"])
MAX_ONET_UPLOAD = 500 * 1024 * 1024
_onet_import_lock = Lock()


@router.get("/dashboard")
def admin_dashboard(admin: AdminUser, db: DbSession):
    return dashboard.overview(db)


@router.post("/onet/import")
def onet_import(
    admin: AdminUser,
    db: DbSession,
    file: UploadFile = File(...),
    version: str = Query(default="user-supplied", max_length=32, pattern=r"^[\w .-]+$"),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise BadRequest("O*NET archive must be a ZIP file")
    if file.size is None or file.size > MAX_ONET_UPLOAD:
        raise PayloadTooLarge("O*NET archive exceeds 500 MB")
    if not _onet_import_lock.acquire(blocking=False):
        raise ConflictError("An import is already in progress.")
    try:
        result = import_onet_zip(db, file.file, version.strip())
        register_import(db, result)
        db.commit()
    except OnetImportError as exc:
        db.rollback()
        raise BadRequest(str(exc)) from None
    finally:
        _onet_import_lock.release()
        file.file.close()
    return {"import_status": "completed", "archive": Path(file.filename).name, **result}


@router.get("/contributions")
def admin_contributions(admin: AdminUser, db: DbSession):
    return contributions.list_for_review(db)


@router.post("/contributions/{contribution_id}/review")
def review_contribution(contribution_id: int, request: ContributionReviewRequest, admin: AdminUser, db: DbSession):
    return contributions.review(db, admin, contribution_id, request)


@router.get("/contributions/{contribution_id}/history")
def contribution_history(contribution_id: int, admin: AdminUser, db: DbSession):
    return contributions.history(db, contribution_id)


@router.post("/datasets/build")
def build_dataset(request: DatasetBuildRequest, admin: AdminUser, db: DbSession):
    return pipeline.create_draft(db, request.name)


@router.get("/datasets")
def list_datasets(admin: AdminUser, db: DbSession):
    return training_repository.list_datasets(db)


@router.get("/datasets/{dataset_id}/records")
def list_dataset_records(dataset_id: int, admin: AdminUser, db: DbSession):
    return pipeline.draft_records(db, dataset_id)


@router.get("/training/history")
def training_history(admin: AdminUser, db: DbSession):
    return training_repository.list_history(db)


@router.get("/models")
def list_models(admin: AdminUser, db: DbSession):
    return training_repository.list_models(db)


@router.post("/models")
def register_model(payload: ModelVersionRequest, admin: AdminUser, db: DbSession):
    return pipeline.register_model(db, payload)
