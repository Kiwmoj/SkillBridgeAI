from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from backend.config import settings

SECRET_CONFIGURED = settings.jwt_secret_configured
# Without a configured secret, sessions are only valid for the lifetime of this process.
SECRET = settings.jwt_secret or token_urlsafe(48)
MINUTES = settings.access_token_minutes

password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = password_hasher.hash(token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except VerificationError:
        return False


def create_token(user_id: int, session_version: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "v": session_version, "iat": now,
         "exp": now + timedelta(minutes=MINUTES), "iss": "skillbridge"},
        SECRET, algorithm="HS256",
    )


def decode_token(token: str) -> tuple[int, int]:
    try:
        payload = jwt.decode(
            token, SECRET, algorithms=["HS256"], issuer="skillbridge",
            options={"require": ["sub", "v", "iat", "exp"]},
        )
        return int(payload["sub"]), int(payload["v"])
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise ValueError("Invalid or expired token") from exc


def recovery_digest(code: str) -> str:
    return sha256(code.strip().encode("utf-8")).hexdigest()
