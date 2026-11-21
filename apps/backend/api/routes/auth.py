from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from apps.backend.api.dependencies import CurrentUser, DbSession
from apps.backend.core import config
from apps.backend.core.exceptions import AuthenticationError
from apps.backend.core.logging import get_logger
from apps.backend.schemas.auth import (
    LoginRequest,
    PasswordConfirmation,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
)
from apps.backend.services.authentication import accounts

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = get_logger(__name__)


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: DbSession):
    user = accounts.register(db, request.name, request.email, request.password)
    return TokenResponse(access_token=accounts.issue_token(user), role=user.role)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, http_request: Request, db: DbSession):
    try:
        user = accounts.authenticate(db, request.email, request.password)
    except AuthenticationError:
        logger.info("Login rejected for client %s: invalid credentials",
                    http_request.client.host if http_request.client else "unknown")
        raise
    return TokenResponse(access_token=accounts.issue_token(user), role=user.role)


@router.get("/me")
def me(user: CurrentUser):
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role, "created_at": user.created_at}


@router.post("/logout")
def logout(user: CurrentUser, db: DbSession):
    accounts.sign_out(db, user)
    return {"signed_out": True}


@router.post("/recovery-code")
def create_recovery_code(request: PasswordConfirmation, user: CurrentUser, db: DbSession):
    code = accounts.create_recovery_code(db, user, request.password)
    return JSONResponse({"recovery_code": code}, headers={"Cache-Control": "no-store"})


@router.post("/reset-password")
def reset_password(request: PasswordResetRequest, db: DbSession):
    accounts.reset_password(db, request.email, request.recovery_code, request.password)
    return {"password_reset": True}


@router.post("/delete-account")
def delete_account(request: PasswordConfirmation, user: CurrentUser, db: DbSession):
    pending = accounts.delete_account(db, user, request.password, config.settings.upload_dir)
    return {"deleted": True, "file_cleanup_pending": pending}
