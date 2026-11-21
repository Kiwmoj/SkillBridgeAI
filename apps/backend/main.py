"""FastAPI application factory.

Routers are mounted twice: under ``/api/v1`` (canonical, documented) and at the historical
unprefixed paths (hidden from the schema) so existing clients keep working.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.backend.api.middleware import RateLimitMiddleware
from apps.backend.api.router import api_router
from apps.backend.core.config import API_PREFIX, APP_VERSION, SCHEMA_REVISION, settings
from apps.backend.core.exceptions import register_exception_handlers
from apps.backend.core.logging import configure_logging, get_logger
from apps.backend.database import connection

configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s %s (environment=%s, database=%s, ai_provider=%s)", app.title, app.version,
                settings.environment, settings.database_backend, settings.ai_provider)
    try:
        with connection.engine.connect() as db:
            revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except SQLAlchemyError as exc:
        logger.error("Database connection failed during startup: %s", type(exc).__name__)
        raise RuntimeError("Check DATABASE_URL and run 'python -m alembic upgrade head'.") from exc
    if revision != SCHEMA_REVISION:
        logger.error("Database schema revision %r does not match the expected %r.", revision, SCHEMA_REVISION)
        raise RuntimeError("Run 'python -m alembic upgrade head' before starting SkillBridge AI.")
    if not settings.jwt_secret_configured:
        logger.warning("JWT_SECRET is not configured; sessions will expire when this process stops.")
    logger.info("Startup checks passed.")
    yield
    connection.engine.dispose()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(title="SkillBridge AI", version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(RateLimitMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=API_PREFIX)
    app.include_router(api_router, include_in_schema=False, deprecated=True)
    return app


app = create_app()
