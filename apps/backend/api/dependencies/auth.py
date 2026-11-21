import logging
from typing import Annotated, Optional

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from apps.backend.api.dependencies.database import DbSession
from apps.backend.core.exceptions import AuthenticationError, AuthorizationError
from apps.backend.core.security import decode_token
from apps.backend.models import User
from apps.backend.repositories import users as users_repository

logger = logging.getLogger(__name__)


def current_user(
    request: Request,
    db: DbSession,
    authorization: Optional[str] = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        logger.info("Rejected unauthenticated request to %s %s", request.method, request.url.path)
        raise AuthenticationError("Authentication required")
    try:
        user_id, session_version = decode_token(authorization.split(" ", 1)[1])
    except (ValueError, TypeError):
        logger.info("Rejected invalid or expired token on %s %s", request.method, request.url.path)
        raise AuthenticationError("Invalid or expired token") from None
    user = users_repository.get_by_id(db, user_id)
    if not user or user.session_version != session_version:
        logger.info("Rejected revoked session on %s %s", request.method, request.url.path)
        raise AuthenticationError("Invalid or expired session")
    return user


def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != "admin":
        raise AuthorizationError("Administrator access required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(admin_user)]

__all__ = ["AdminUser", "CurrentUser", "Session", "admin_user", "current_user"]
