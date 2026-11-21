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
    token = register(client)["access_token"]

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
