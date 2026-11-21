"""Domain errors raised by services and the handlers that turn them into HTTP responses.

Every error response has the shape ``{"detail": <message or list>, "error": <category>}``.
``detail`` keeps the historical contract used by the desktop client; ``error`` is an additive
machine-readable category: validation, authentication, authorization, not_found, conflict,
rate_limited, ai_provider, database, or server.
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

STATUS_CATEGORIES = {
    400: "validation", 401: "authentication", 403: "authorization", 404: "not_found",
    409: "conflict", 413: "validation", 422: "validation", 429: "rate_limited", 503: "ai_provider",
}


class AppError(Exception):
    status_code = 400
    error = "validation"

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class ValidationFailure(AppError):
    status_code = 422
    error = "validation"


class BadRequest(AppError):
    status_code = 400
    error = "validation"


class PayloadTooLarge(AppError):
    status_code = 413
    error = "validation"


class AuthenticationError(AppError):
    status_code = 401
    error = "authentication"


class AuthorizationError(AppError):
    status_code = 403
    error = "authorization"


class NotFoundError(AppError):
    status_code = 404
    error = "not_found"


class ConflictError(AppError):
    status_code = 409
    error = "conflict"


class ExternalServiceError(AppError):
    """An AI provider or other upstream dependency failed; the request can be retried later."""
    status_code = 503
    error = "ai_provider"


def error_response(status_code: int, detail, error: str | None = None, headers: dict | None = None) -> JSONResponse:
    category = error or STATUS_CATEGORIES.get(status_code, "server" if status_code >= 500 else "validation")
    return JSONResponse(status_code=status_code, content={"detail": detail, "error": category}, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        if exc.status_code in (401, 403):
            logger.info("%s on %s %s", exc.error, request.method, request.url.path)
        return error_response(exc.status_code, exc.detail, exc.error)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(exc.status_code, exc.detail, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        errors = [{"loc": error["loc"], "msg": error["msg"]} for error in exc.errors()]
        logger.info("Invalid request %s %s: %d validation error(s)", request.method, request.url.path, len(errors))
        return error_response(422, errors, "validation")

    @app.exception_handler(SQLAlchemyError)
    async def database_failure(request: Request, exc: SQLAlchemyError):
        logger.error("Database error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
        return error_response(503, "The database is unavailable. Try again shortly.", "database")

    @app.exception_handler(Exception)
    async def unexpected_failure(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "Internal server error.", "server")
