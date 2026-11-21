"""Centralized backend configuration.

Every backend module reads its settings from here so that environment handling,
validation, and the development/production split live in one place.
"""
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()

ENVIRONMENTS = ("development", "production")
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
PLACEHOLDER_SECRETS = ("change-this-secret-in-production", "local-development-only-change-me")
DEFAULT_DATABASE_URL = "sqlite:///./skillbridge.db"
API_PREFIX = "/api/v1"
SCHEMA_REVISION = "20261123_skill_level"
APP_VERSION = "2.0.0"


class ConfigurationError(RuntimeError):
    pass


def normalize_database_url(value: str) -> str:
    url = value.strip()
    if not url:
        raise ConfigurationError("DATABASE_URL is empty.")
    # Railway and Heroku-style URLs use the legacy scheme; SQLAlchemy needs the psycopg driver name.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    scheme = url.split(":", 1)[0].lower().split("+", 1)[0]
    if scheme not in {"sqlite", "postgresql"}:
        raise ConfigurationError("DATABASE_URL must be a sqlite:// or postgresql:// URL.")
    return url


def validate_origin(value: str, production: bool) -> str:
    origin = value.strip().rstrip("/")
    parts = urlsplit(origin)
    if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.path or parts.query
            or parts.fragment or parts.username is not None or parts.password is not None):
        raise ConfigurationError(f"ALLOWED_ORIGINS entry is not an origin (scheme://host[:port]): {origin!r}")
    if production and parts.scheme != "https" and parts.hostname not in LOCAL_HOSTS:
        raise ConfigurationError("ALLOWED_ORIGINS must use HTTPS in production.")
    return origin


def validate_public_url(value: str, production: bool) -> str | None:
    url = value.strip().rstrip("/")
    if not url:
        return None
    try:
        parts = urlsplit(url)
        _port = parts.port
    except ValueError as exc:
        raise ConfigurationError("BACKEND_URL is not a valid URL.") from exc
    if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.path or parts.query
            or parts.fragment or parts.username is not None or parts.password is not None):
        raise ConfigurationError("BACKEND_URL must look like https://host[:port] with no path.")
    if parts.scheme != "https" and (production or parts.hostname not in LOCAL_HOSTS):
        raise ConfigurationError("BACKEND_URL must use HTTPS unless it points at a local loopback server.")
    return url


def _integer(env: Mapping[str, str], name: str, default: int, lowest: int, highest: int) -> int:
    raw = env.get(name, "").strip()
    try:
        number = int(raw) if raw else default
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a whole number.") from exc
    if not lowest <= number <= highest:
        raise ConfigurationError(f"{name} must be between {lowest} and {highest}.")
    return number


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    jwt_secret: str | None
    access_token_minutes: int
    allowed_origins: tuple[str, ...]
    upload_dir: Path
    ai_provider: str
    gemini_api_key: str | None
    gemini_model: str
    port: int
    public_url: str | None
    log_level: str
    onet_auto_import: bool = False
    onet_archive_url: str = "https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip"
    onet_skip_files: frozenset[str] = frozenset()

    @property
    def production(self) -> bool:
        return self.environment == "production"

    @property
    def database_backend(self) -> str:
        return "sqlite" if self.database_url.startswith("sqlite") else "postgresql"

    @property
    def jwt_secret_configured(self) -> bool:
        return self.jwt_secret is not None


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build validated settings from the environment; raise ConfigurationError instead of starting badly."""
    env = os.environ if env is None else env
    environment = env.get("APP_ENV", "").strip().lower() or "development"
    if environment not in ENVIRONMENTS:
        raise ConfigurationError("APP_ENV must be 'development' or 'production'.")
    production = environment == "production"

    database_url = normalize_database_url(env.get("DATABASE_URL", "") or DEFAULT_DATABASE_URL)
    if production and database_url.startswith("sqlite"):
        raise ConfigurationError("Production requires a PostgreSQL DATABASE_URL; SQLite is for local development only.")

    secret = env.get("JWT_SECRET", "").strip()
    secret_configured = len(secret.encode("utf-8")) >= 32 and secret not in PLACEHOLDER_SECRETS
    if production and not secret_configured:
        raise ConfigurationError("Production requires a random JWT_SECRET of at least 32 bytes.")

    origins = tuple(
        validate_origin(entry, production) for entry in env.get("ALLOWED_ORIGINS", "").split(",") if entry.strip()
    )

    log_level = env.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    if not isinstance(logging.getLevelName(log_level), int):
        raise ConfigurationError("LOG_LEVEL must be a standard logging level such as INFO or DEBUG.")

    return Settings(
        environment=environment,
        database_url=database_url,
        jwt_secret=secret if secret_configured else None,
        access_token_minutes=_integer(env, "ACCESS_TOKEN_MINUTES", 60, 1, 1440),
        allowed_origins=origins,
        upload_dir=Path(env.get("UPLOAD_DIR", "").strip() or "./uploads").resolve(),
        ai_provider=(env.get("AI_PROVIDER", "").strip() or "gemini").lower(),
        gemini_api_key=env.get("GEMINI_API_KEY", "").strip() or None,
        gemini_model=env.get("GEMINI_MODEL", "").strip(),
        port=_integer(env, "PORT", 8000, 1, 65535),
        public_url=validate_public_url(env.get("BACKEND_URL", ""), production),
        log_level=log_level,
        onet_auto_import=env.get("ONET_AUTO_IMPORT", "").strip().lower() in {"1", "true", "yes"},
        onet_archive_url=env.get("ONET_ARCHIVE_URL", "").strip()
        or "https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip",
        onet_skip_files=frozenset(
            item.strip().lower() for item in env.get("ONET_SKIP_FILES", "").split(",") if item.strip()
        ),
    )


settings = load_settings()
