import io
import zipfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.core import config
from apps.backend.core.security import SECRET
from apps.backend.database import connection, make_engine
from apps.backend.database.session import get_db
from apps.backend.main import app
from apps.backend.services.ai.providers import AIProviderError
from apps.backend.services.ai.service import ai_service
from tests.conftest import migrate
from tests.fixtures.api import API, admin_token, auth, register
from tests.fixtures.onet import make_onet_archive

def test_startup_refuses_unmigrated_database(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    monkeypatch.setattr(connection, "engine", engine)
    try:
        with pytest.raises(RuntimeError, match="alembic upgrade head"):
            with TestClient(app):
                pass
    finally:
        engine.dispose()


def test_health_reports_database_failure_without_claiming_health(client, tmp_path):  # noqa: F811
    healthy = client.get(f"{API}/health").json()
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
        response = client.get(f"{API}/health")
    finally:
        app.dependency_overrides[get_db] = working_session
    assert response.status_code == 503
    assert response.json()["database"] == "unhealthy" and response.json()["status"] == "unhealthy"
    assert client.get(f"{API}/health").status_code == 200


def test_me_duplicates_and_invalid_logins(client):  # noqa: F811
    assert client.get(f"{API}/auth/me").status_code == 401
    token = register(client, name="Student One", email="Student@Example.com")["access_token"]
    me = client.get(f"{API}/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "student@example.com" and me.json()["role"] == "student"
    assert me.json()["name"] == "Student One" and "password" not in str(me.json()).lower()

    duplicate = client.post(f"{API}/auth/register", json={
        "name": "Again", "email": "STUDENT@example.com", "password": "another-password",
    })
    assert duplicate.status_code == 409
    assert client.post(f"{API}/auth/login", json={"email": "student@example.com", "password": "wrong"}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": "strong-password"}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "not-an-email", "password": "strong-password"}).status_code == 422


def test_jwt_validation_rejects_tampered_foreign_and_expired_tokens(client):  # noqa: F811
    token = register(client)["access_token"]
    user_id = client.get(f"{API}/auth/me", headers=auth(token)).json()["id"]
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "v": 0, "iat": now, "exp": now + timedelta(minutes=5), "iss": "skillbridge"}

    expired = jwt.encode({**claims, "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)}, SECRET, "HS256")
    foreign = jwt.encode(claims, "another-secret-another-secret-another", "HS256")
    unknown_user = jwt.encode({**claims, "sub": str(user_id + 99)}, SECRET, "HS256")
    for bad in (expired, foreign, unknown_user, token[:-4] + "abcd", "not-a-token"):
        assert client.get(f"{API}/auth/me", headers=auth(bad)).status_code == 401
    assert client.get(f"{API}/auth/me", headers={"Authorization": token}).status_code == 401
    assert client.get(f"{API}/auth/me", headers=auth(token)).status_code == 200


def test_registration_persists_across_connections(tmp_path, monkeypatch):
    database = f"sqlite:///{tmp_path / 'persist.db'}"
    engine = make_engine(database)
    migrate(engine)
    monkeypatch.setattr(connection, "engine", engine)
    monkeypatch.setattr(config, "settings", replace(config.settings, upload_dir=tmp_path / "uploads"))

    def session():
        with Session(connection.engine) as db:
            yield db

    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as first:
            token = register(first, email="persist@example.com")["access_token"]
            assert first.put(f"{API}/profile", headers=auth(token), json={"goals": "Keep this"}).status_code == 200
        engine.dispose()
        monkeypatch.setattr(connection, "engine", make_engine(database))
        with TestClient(app) as second:
            login = second.post(f"{API}/auth/login", json={"email": "persist@example.com", "password": "strong-password"})
            assert login.status_code == 200
            assert second.get(f"{API}/profile", headers=auth(login.json()["access_token"])).json()["goals"] == "Keep this"
    finally:
        app.dependency_overrides.clear()
        connection.engine.dispose()


def test_legacy_unprefixed_paths_still_work(client):
    """Older desktop builds call the unversioned paths; they must keep working but stay out of the schema."""
    token = register(client)["access_token"]
    assert client.get("/health").json()["status"] == "healthy"
    assert client.get("/profile", headers=auth(token)).status_code == 200
    assert client.get("/auth/me", headers=auth(token)).json()["email"] == "student@example.com"
    paths = client.get("/openapi.json").json()["paths"]
    assert f"{API}/auth/me" in paths and "/auth/me" not in paths


def test_api_error_responses_are_json_and_do_not_leak(client, monkeypatch):  # noqa: F811
    assert client.get(f"{API}/no-such-route").status_code == 404
    invalid = client.post(f"{API}/auth/register", json={"name": "", "email": "bad", "password": "short"})
    assert invalid.status_code == 422
    assert invalid.json()["error"] == "validation"
    assert all(set(item) == {"loc", "msg"} for item in invalid.json()["detail"])
    assert "short" not in invalid.text
    denied = client.get(f"{API}/profile")
    assert denied.status_code == 401 and denied.json()["error"] == "authentication"

    def explode(*_args, **_kwargs):
        raise RuntimeError("database password: hunter2")

    monkeypatch.setattr(ai_service, "status", explode)
    with TestClient(app, raise_server_exceptions=False) as tolerant:
        response = tolerant.get(f"{API}/health")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error.", "error": "server"}
    assert "hunter2" not in response.text
