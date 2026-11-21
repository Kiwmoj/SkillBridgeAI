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

def test_registration_login_profile_and_health(client):
    registration = register(client)
    token = registration["access_token"]
    profile = client.put(f"{API}/profile",
        headers=auth(token),
        json={
            "education": "Community college",
            "interests": "Nursing",
            "goals": "Become a nurse",
            "location": "Seattle",
        },
    )
    assert profile.status_code == 200
    assert profile.json()["interests"] == "Nursing"
    login = client.post(f"{API}/auth/login",
        json={
            "email": "student@example.com",
            "password": "strong-password",
        },
    )
    assert login.status_code == 200
    assert client.get(f"{API}/health").json()["database"] == "healthy"


def test_authentication_and_user_data_isolation(client):
    token_a = register(client, email="a@example.com")["access_token"]
    token_b = register(client, name="B", email="b@example.com")["access_token"]
    client.put(f"{API}/profile",
        headers=auth(token_a),
        json={"goals": "A private goal"},
    )
    profile_b = client.get(f"{API}/profile", headers=auth(token_b))
    assert profile_b.status_code == 200
    assert profile_b.json().get("goals") is None
    assert client.get(f"{API}/profile").status_code == 401


def test_password_recovery_and_account_deletion(client, monkeypatch):
    account = register(client)
    assert account["role"] == "student"
    original = auth(account["access_token"])
    assert client.get(f"{API}/admin/dashboard", headers=original).status_code == 403
    current = {"password": "strong-password"}
    generated = client.post(f"{API}/auth/recovery-code", headers=original, json=current)
    assert generated.is_success
    reset = {"email": "student@example.com", "password": "new-example-password",
             "recovery_code": generated.json()["recovery_code"]}
    assert client.post(f"{API}/auth/reset-password", json=reset).is_success
    assert client.post(f"{API}/auth/reset-password", json=reset).status_code == 400
    assert client.get(f"{API}/profile", headers=original).status_code == 401
    credentials = {"email": reset["email"], "password": reset["password"]}
    signed_in = client.post(f"{API}/auth/login", json=credentials)
    assert signed_in.is_success
    authorized = auth(signed_in.json()["access_token"])
    assert client.post(f"{API}/auth/logout", headers=authorized).is_success
    assert client.get(f"{API}/profile", headers=authorized).status_code == 401
    signed_in = client.post(f"{API}/auth/login", json=credentials)
    authorized = auth(signed_in.json()["access_token"])
    assert client.post(f"{API}/auth/delete-account", headers=authorized, json=current).status_code == 403
    assert client.post(f"{API}/auth/delete-account", headers=authorized, json={"password": reset["password"]}).is_success
    assert client.post(f"{API}/auth/login", json=credentials).status_code == 401
