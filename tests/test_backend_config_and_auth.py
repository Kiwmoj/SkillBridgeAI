from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import backend.main as main_module
from backend.config import ConfigurationError, load_settings
from backend.database import get_db, make_engine
from backend.main import app
from backend.security import SECRET
from tests.test_api import auth, client, register  # noqa: F401 - shared fixture and helpers

PRODUCTION_ENV = {
    "APP_ENV": "production",
    "DATABASE_URL": "postgres://user:secret@db.internal:5432/skillbridge",
    "JWT_SECRET": "x" * 48,
    "ALLOWED_ORIGINS": "https://app.example.com",
    "BACKEND_URL": "https://api.example.com",
    "PORT": "6000",
}


def test_settings_normalise_and_validate_configuration():
    settings = load_settings(PRODUCTION_ENV)
    assert settings.database_url == "postgresql+psycopg://user:secret@db.internal:5432/skillbridge"
    assert settings.database_backend == "postgresql"
    assert settings.allowed_origins == ("https://app.example.com",)
    assert settings.port == 6000 and settings.production and settings.jwt_secret_configured

    local = load_settings({})
    assert local.environment == "development" and local.database_backend == "sqlite"
    assert local.jwt_secret is None and local.public_url is None

    rejected = [
        {**PRODUCTION_ENV, "DATABASE_URL": "sqlite:///./skillbridge.db"},
        {**PRODUCTION_ENV, "JWT_SECRET": "change-this-secret-in-production"},
        {**PRODUCTION_ENV, "JWT_SECRET": "too-short"},
        {**PRODUCTION_ENV, "ALLOWED_ORIGINS": "http://app.example.com"},
        {**PRODUCTION_ENV, "ALLOWED_ORIGINS": "https://app.example.com/api"},
        {**PRODUCTION_ENV, "BACKEND_URL": "api.example.com"},
        {"DATABASE_URL": "mysql://user@host/db"},
        {"ACCESS_TOKEN_MINUTES": "0"},
        {"APP_ENV": "staging"},
        {"LOG_LEVEL": "LOUD"},
    ]
    for environment in rejected:
        with pytest.raises(ConfigurationError):
            load_settings(environment)


def test_startup_refuses_unmigrated_database(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    monkeypatch.setattr(main_module, "engine", engine)
    try:
        with pytest.raises(RuntimeError, match="alembic upgrade head"):
            with TestClient(app):
                pass
    finally:
        engine.dispose()


def test_health_reports_database_failure_without_claiming_health(client, tmp_path):  # noqa: F811
    healthy = client.get("/health").json()
    assert healthy["status"] == "healthy" and healthy["database"] == "healthy"
    assert healthy["environment"] == "development" and healthy["database_backend"] == "sqlite"
    assert healthy["version"] == app.version
    assert not any(key in healthy for key in ("jwt_secret", "database_url", "gemini_api_key"))

    broken = make_engine(f"sqlite:///{tmp_path / 'missing-directory' / 'absent.db'}")

    def failing_session():
        with Session(broken) as db:
            yield db

    working_session = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = failing_session
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides[get_db] = working_session
    assert response.status_code == 503
    assert response.json()["database"] == "unhealthy" and response.json()["status"] == "unhealthy"
    assert client.get("/health").status_code == 200


def test_me_duplicates_and_invalid_logins(client):  # noqa: F811
    assert client.get("/auth/me").status_code == 401
    token = register(client, name="Student One", email="Student@Example.com")["access_token"]
    me = client.get("/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "student@example.com" and me.json()["role"] == "student"
    assert me.json()["name"] == "Student One" and "password" not in str(me.json()).lower()

    duplicate = client.post("/auth/register", json={
        "name": "Again", "email": "STUDENT@example.com", "password": "another-password",
    })
    assert duplicate.status_code == 409
    assert client.post("/auth/login", json={"email": "student@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/auth/login", json={"email": "nobody@example.com", "password": "strong-password"}).status_code == 401
    assert client.post("/auth/login", json={"email": "not-an-email", "password": "strong-password"}).status_code == 422


def test_jwt_validation_rejects_tampered_foreign_and_expired_tokens(client):  # noqa: F811
    token = register(client)["access_token"]
    user_id = client.get("/auth/me", headers=auth(token)).json()["id"]
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "v": 0, "iat": now, "exp": now + timedelta(minutes=5), "iss": "skillbridge"}

    expired = jwt.encode({**claims, "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)}, SECRET, "HS256")
    foreign = jwt.encode(claims, "another-secret-another-secret-another", "HS256")
    unknown_user = jwt.encode({**claims, "sub": str(user_id + 99)}, SECRET, "HS256")
    for bad in (expired, foreign, unknown_user, token[:-4] + "abcd", "not-a-token"):
        assert client.get("/auth/me", headers=auth(bad)).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": token}).status_code == 401
    assert client.get("/auth/me", headers=auth(token)).status_code == 200


def test_registration_persists_across_connections(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'persist.db'}")
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(main_module, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(main_module, "_rate_windows", {})
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    def session():
        with Session(main_module.engine) as db:
            yield db

    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as first:
            token = register(first, email="persist@example.com")["access_token"]
            assert first.put("/profile", headers=auth(token), json={"goals": "Keep this"}).status_code == 200
        engine.dispose()
        monkeypatch.setattr(main_module, "engine", make_engine(f"sqlite:///{tmp_path / 'persist.db'}"))
        with TestClient(app) as second:
            login = second.post("/auth/login", json={"email": "persist@example.com", "password": "strong-password"})
            assert login.status_code == 200
            assert second.get("/profile", headers=auth(login.json()["access_token"])).json()["goals"] == "Keep this"
    finally:
        app.dependency_overrides.clear()
        main_module.engine.dispose()


def test_api_error_responses_are_json_and_do_not_leak(client, monkeypatch):  # noqa: F811
    assert client.get("/no-such-route").status_code == 404
    invalid = client.post("/auth/register", json={"name": "", "email": "bad", "password": "short"})
    assert invalid.status_code == 422
    assert all(set(item) == {"loc", "msg"} for item in invalid.json()["detail"])
    assert "short" not in invalid.text

    def explode(*_args, **_kwargs):
        raise RuntimeError("database password: hunter2")

    monkeypatch.setattr(main_module.ai, "status", explode)
    with TestClient(app, raise_server_exceptions=False) as tolerant:
        response = tolerant.get("/health")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}
    assert "hunter2" not in response.text
