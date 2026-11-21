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

def test_portfolio_upload_validation_and_evaluation(monkeypatch, client):
    token = register(client)["access_token"]
    image = Image.new("RGB", (40, 40), color=(25, 70, 130))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    monkeypatch.setattr(
        ai_service,
        "generate_with_image",
        lambda prompt, image_bytes, mime_type: "This is an AI-generated portfolio review.",
    )
    uploaded = client.post(f"{API}/portfolio/upload",
        headers=auth(token),
        files={
            "file": (
                "portfolio.png",
                buffer.getvalue(),
                "image/png",
            )
        },
    )
    assert uploaded.status_code == 200
    evaluation = client.post(f"{API}/portfolio/{uploaded.json()['id']}/evaluate",
        headers=auth(token),
        json={"send_to_provider": True},
    )
    assert evaluation.status_code == 200
    assert "AI-generated" in evaluation.json()["evaluation"]

    invalid = client.post(f"{API}/portfolio/upload",
        headers=auth(token),
        files={
            "file": (
                "notes.txt",
                b"not an image",
                "text/plain",
            )
        },
    )
    assert invalid.status_code == 400
