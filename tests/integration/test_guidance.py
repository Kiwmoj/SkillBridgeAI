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

def test_ai_outage_is_reported_without_fake_response(monkeypatch, client):
    """A configured provider that fails must return 503, never a fabricated answer."""
    token = register(client)["access_token"]
    monkeypatch.setattr(ai_service, "status", lambda: {"provider": "gemini", "configured": True, "reachable": None})

    def unavailable(prompt):
        raise AIProviderError("Gemini is unavailable")

    monkeypatch.setattr(ai_service, "generate", unavailable)
    response = client.post(f"{API}/ai/generate",
        headers=auth(token),
        json={
            "purpose": "Career guidance",
            "question": "What skills do nurses need?",
        },
    )
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


def test_guidance_falls_back_to_sources_without_a_key(client, tmp_path):
    """With no provider configured, guidance returns real source-based info, clearly not AI-generated."""
    token = register(client)["access_token"]
    archive, _ = make_onet_archive(tmp_path)
    admin = auth(admin_token(client))
    with archive.open("rb") as stream:
        assert client.post(f"{API}/admin/onet/import?version=29.0", headers=admin,
                           files={"file": ("onet.zip", stream)}).is_success

    response = client.post(f"{API}/ai/generate", headers=auth(token),
                           json={"purpose": "Career Reality Check", "question": "Registered Nurses"})
    assert response.status_code == 200
    body = response.json()
    assert body["generated"] is False
    assert body["provider"] == "sources"
    assert "not AI-generated" in body["answer"]
    assert body["sources"]  # retrieved official O*NET sources are attached

