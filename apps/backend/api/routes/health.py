from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.backend.api.dependencies import DbSession
from apps.backend.core.config import APP_VERSION, settings
from apps.backend.core.exceptions import error_response
from apps.backend.core.logging import get_logger
from apps.backend.core.security import SECRET_CONFIGURED
from apps.backend.repositories import training as training_repository
from apps.backend.services.ai.service import ai_service

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
def health(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
        latest = training_repository.latest_imported_dataset(db)
    except SQLAlchemyError as exc:
        logger.error("Database health check failed: %s", type(exc).__name__)
        return error_response(503, "The database is unavailable.", "database") if False else _unhealthy()
    return {
        "status": "healthy", "database": "healthy", "database_backend": settings.database_backend,
        "ai": ai_service.status(), "version": APP_VERSION, "environment": settings.environment,
        "onet_version": latest.name.removeprefix("O*NET ") if latest else None,
        "jwt_secret_configured": SECRET_CONFIGURED,
    }


def _unhealthy():
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=503, content={
        "status": "unhealthy", "database": "unhealthy", "version": APP_VERSION,
        "environment": settings.environment,
    })
