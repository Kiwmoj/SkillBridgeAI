"""Account lifecycle: registration, credential checks, sessions, recovery, and deletion."""
import logging
from pathlib import Path
from secrets import compare_digest, token_urlsafe

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.backend.core.exceptions import AuthenticationError, AuthorizationError, BadRequest, ConflictError
from apps.backend.core.security import (
    DUMMY_PASSWORD_HASH,
    create_token,
    hash_password,
    recovery_digest,
    verify_password,
)
from apps.backend.models import User
from apps.backend.repositories import community as community_repository
from apps.backend.repositories import portfolio as portfolio_repository
from apps.backend.repositories import users as users_repository
from apps.backend.services.training.pipeline import invalidate_datasets

logger = logging.getLogger(__name__)


def register(db: Session, name: str, email: str, password: str) -> User:
    if users_repository.get_by_email(db, email):
        raise ConflictError("Email is already registered")
    user = users_repository.add_user(db, email, name.strip(), hash_password(password))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Email is already registered") from None
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = users_repository.get_by_email(db, email)
    # Always verify against a hash so response timing does not reveal whether the email exists.
    verified = verify_password(password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if not user or not verified:
        raise AuthenticationError("Invalid email or password")
    return user


def issue_token(user: User) -> str:
    return create_token(user.id, user.session_version)


def sign_out(db: Session, user: User) -> None:
    users_repository.revoke_sessions(db, user.id)
    db.commit()


def create_recovery_code(db: Session, user: User, password: str) -> str:
    if not verify_password(password, user.password_hash):
        raise AuthorizationError("Current password is incorrect.")
    code = token_urlsafe(32)
    user.recovery_hash = recovery_digest(code)
    db.commit()
    return code


def reset_password(db: Session, email: str, code: str, new_password: str) -> None:
    user = users_repository.get_by_email(db, email)
    digest = recovery_digest(code)
    if not user or not user.recovery_hash or not compare_digest(digest, user.recovery_hash):
        raise BadRequest("Email or recovery code is invalid.")
    if users_repository.apply_password_reset(db, user.id, digest, hash_password(new_password)) != 1:
        raise BadRequest("Email or recovery code is invalid.")
    db.commit()


def delete_account(db: Session, user: User, password: str, upload_dir: Path) -> int:
    """Delete the student's account and private data; return the number of files that could not be removed."""
    if user.role != "student":
        raise ConflictError("Administrator accounts require operator-managed deletion.")
    if not verify_password(password, user.password_hash):
        raise AuthorizationError("Current password is incorrect.")
    community_repository.lock_community_writes(db)
    invalidate_datasets(db, community_repository.user_contribution_ids(user.id))
    community_repository.delete_user_community_rows(db, user.id)
    files = portfolio_repository.stored_paths(db, user.id)
    users_repository.delete_user_records(db, user)
    db.commit()
    failures = 0
    for filename in files:
        try:
            (upload_dir / Path(filename).name).unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove a private portfolio file after account deletion.")
            failures += 1
    return failures
